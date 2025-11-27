use crate::cli::StyleMode;
use anyhow::Result;
use avt::{Color, Pen};
use futures_util::{stream, Stream, StreamExt};
use serde::Serialize;
use serde_json::json;
use std::collections::HashMap;
use std::future;
use std::time::{Duration, Instant};
use tokio::sync::{broadcast, mpsc, oneshot};
use tokio_stream::wrappers::{errors::BroadcastStreamRecvError, BroadcastStream};

#[derive(Debug, Clone, Serialize)]
pub struct PenJson {
    #[serde(skip_serializing_if = "Option::is_none")]
    fg: Option<ColorJson>,
    #[serde(skip_serializing_if = "Option::is_none")]
    bg: Option<ColorJson>,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    attrs: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(untagged)]
pub enum ColorJson {
    Indexed { indexed: u8 },
    Rgb { rgb: [u8; 3] },
}

impl From<&Pen> for PenJson {
    fn from(pen: &Pen) -> Self {
        let mut attrs = Vec::new();
        if pen.is_bold() { attrs.push("bold".to_string()); }
        if pen.is_faint() { attrs.push("faint".to_string()); }
        if pen.is_italic() { attrs.push("italic".to_string()); }
        if pen.is_underline() { attrs.push("underline".to_string()); }
        if pen.is_strikethrough() { attrs.push("strikethrough".to_string()); }
        if pen.is_blink() { attrs.push("blink".to_string()); }
        if pen.is_inverse() { attrs.push("inverse".to_string()); }

        PenJson {
            fg: pen.foreground().map(|c| match c {
                Color::Indexed(i) => ColorJson::Indexed { indexed: i },
                Color::RGB(rgb) => ColorJson::Rgb { rgb: [rgb.r, rgb.g, rgb.b] },
            }),
            bg: pen.background().map(|c| match c {
                Color::Indexed(i) => ColorJson::Indexed { indexed: i },
                Color::RGB(rgb) => ColorJson::Rgb { rgb: [rgb.r, rgb.g, rgb.b] },
            }),
            attrs,
        }
    }
}

pub struct Session {
    vt: avt::Vt,
    broadcast_tx: broadcast::Sender<Event>,
    stream_time: f64,
    start_time: Instant,
    last_event_time: Instant,
    pending_pid: Option<i32>,
    style_mode: StyleMode,
}

#[derive(Clone, Debug)]
pub struct StyleData {
    char_map: Vec<Vec<char>>,
    style_map: Vec<Vec<usize>>,
    styles: HashMap<String, PenJson>,
}

#[derive(Clone, Debug)]
pub enum Event {
    Init(f64, usize, usize, i32, String, String, Option<StyleData>),
    Output(f64, String),
    Resize(f64, usize, usize),
    Snapshot(usize, usize, String, String, Option<StyleData>),
    Pid(f64, i32),
    ExitCode(f64, i32),
    Debug(f64, String),
    Completed(f64),
}

pub struct Client(oneshot::Sender<Subscription>);

pub struct Subscription {
    init: Event,
    broadcast_rx: broadcast::Receiver<Event>,
}

impl Session {
    pub fn new(cols: usize, rows: usize) -> Self {
        let (broadcast_tx, _) = broadcast::channel(1024);
        let now = Instant::now();

        Self {
            vt: build_vt(cols, rows),
            broadcast_tx,
            stream_time: 0.0,
            start_time: now,
            last_event_time: now,
            pending_pid: None,
            style_mode: StyleMode::Plain,
        }
    }

    pub fn output(&mut self, data: String) {
        self.vt.feed_str(&data);
        let time = self.start_time.elapsed().as_secs_f64();
        let _ = self.broadcast_tx.send(Event::Output(time, data));
        self.stream_time = time;
        self.last_event_time = Instant::now();
    }

    pub fn resize(&mut self, cols: usize, rows: usize) {
        resize_vt(&mut self.vt, cols, rows);
        let time = self.start_time.elapsed().as_secs_f64();
        let _ = self.broadcast_tx.send(Event::Resize(time, cols, rows));
        self.stream_time = time;
        self.last_event_time = Instant::now();
    }

    pub fn snapshot(&self) {
        let (cols, rows) = self.vt.size();
        let style_data = match self.style_mode {
            StyleMode::Styled => {
                let (pen_to_id, styles) = self.build_style_palette();
                Some(StyleData {
                    char_map: self.build_char_map(),
                    style_map: self.build_style_map(&pen_to_id),
                    styles,
                })
            }
            StyleMode::Plain => None,
        };

        let _ = self.broadcast_tx.send(Event::Snapshot(
            cols,
            rows,
            self.vt.dump(),
            self.text_view(),
            style_data,
        ));
    }

    pub fn emit_pid(&mut self, pid: i32) {
        self.pending_pid = Some(pid);

        let time = self.start_time.elapsed().as_secs_f64();
        let _ = self.broadcast_tx.send(Event::Pid(time, pid));
        self.stream_time = time;
        self.last_event_time = Instant::now();
    }

    pub fn emit_exit_code(&mut self, exit_code: i32) {
        let time = self.start_time.elapsed().as_secs_f64();
        let _ = self.broadcast_tx.send(Event::ExitCode(time, exit_code));
        self.stream_time = time;
        self.last_event_time = Instant::now();
    }

    pub fn emit_command_completed(&mut self) {
        let time = self.start_time.elapsed().as_secs_f64();
        let _ = self.broadcast_tx.send(Event::Completed(time));
        self.stream_time = time;
        self.last_event_time = Instant::now();
    }

    pub fn emit_debug_event(&mut self, message: &str) {
        let time = self.start_time.elapsed().as_secs_f64();
        let _ = self.broadcast_tx.send(Event::Debug(time, message.to_string()));
        self.stream_time = time;
        self.last_event_time = Instant::now();
    }

    pub fn cursor_key_app_mode(&self) -> bool {
        self.vt.cursor_key_app_mode()
    }

    pub fn set_style_mode(&mut self, style_mode: StyleMode) {
        self.style_mode = style_mode;
    }

    pub fn subscribe(&self) -> Subscription {
        let (cols, rows) = self.vt.size();
        let style_data = match self.style_mode {
            StyleMode::Styled => {
                let (pen_to_id, styles) = self.build_style_palette();
                Some(StyleData {
                    char_map: self.build_char_map(),
                    style_map: self.build_style_map(&pen_to_id),
                    styles,
                })
            }
            StyleMode::Plain => None,
        };

        let init = Event::Init(
            self.elapsed_time(),
            cols,
            rows,
            self.pending_pid.unwrap_or(0),
            self.vt.dump(),
            self.text_view(),
            style_data,
        );

        let broadcast_rx = self.broadcast_tx.subscribe();

        if let Some(pid) = self.pending_pid {
            let time = self.elapsed_time();
            let _ = self.broadcast_tx.send(Event::Pid(time, pid));
        }

        Subscription { init, broadcast_rx }
    }

    fn elapsed_time(&self) -> f64 {
        self.stream_time + self.last_event_time.elapsed().as_secs_f64()
    }

    fn text_view(&self) -> String {
        self.vt
            .view()
            .iter()
            .map(|l| l.text())
            .collect::<Vec<_>>()
            .join("\n")
    }

    fn build_style_palette(&self) -> (HashMap<String, usize>, HashMap<String, PenJson>) {
        let mut pen_to_id = HashMap::new();
        let mut styles = HashMap::new();
        // Reserve ID 0 for default pen
        let default_pen = Pen::default();
        let default_key = self.pen_to_key(&default_pen);
        pen_to_id.insert(default_key, 0);
        styles.insert("0".to_string(), PenJson::from(&default_pen));
        let mut next_id = 1;

        for line in self.vt.view() {
            for cell in line.cells() {
                if cell.width() > 0 {
                    let pen = *cell.pen();
                    let pen_key = self.pen_to_key(&pen);
                    if let std::collections::hash_map::Entry::Vacant(e) = pen_to_id.entry(pen_key) {
                        e.insert(next_id);
                        styles.insert(next_id.to_string(), PenJson::from(&pen));
                        next_id += 1;
                    }
                }
            }
        }

        (pen_to_id, styles)
    }

    fn pen_to_key(&self, pen: &Pen) -> String {
        // Create a unique string key for the pen
        format!("{:?}", pen)
    }

    fn build_char_map(&self) -> Vec<Vec<char>> {
        let (cols, _rows) = self.vt.size();
        self.vt
            .view()
            .iter()
            .map(|line| {
                let mut char_row = Vec::with_capacity(cols);
                for cell in line.cells() {
                    char_row.push(cell.char());
                }
                // Ensure we have exactly cols characters, pad with spaces if needed
                char_row.resize(cols, ' ');
                char_row
            })
            .collect()
    }

    fn build_style_map(&self, pen_to_id: &HashMap<String, usize>) -> Vec<Vec<usize>> {
        let (cols, _rows) = self.vt.size();
        self.vt
            .view()
            .iter()
            .map(|line| {
                let mut style_row = Vec::with_capacity(cols);
                for cell in line.cells() {
                    let pen_key = self.pen_to_key(cell.pen());
                    style_row.push(*pen_to_id.get(&pen_key).unwrap_or(&0));
                }
                // Ensure we have exactly cols style IDs, pad with default style if needed
                style_row.resize(cols, 0);
                style_row
            })
            .collect()
    }
}

impl Event {
    pub fn to_json(&self) -> serde_json::Value {
        match self {
            Event::Init(_time, cols, rows, pid, seq, text, style_data) => {
                let mut data = json!({
                    "cols": cols,
                    "rows": rows,
                    "pid": pid,
                    "seq": seq,
                    "text": text,
                });

                if let Some(style_data) = style_data {
                    let data_obj = data.as_object_mut().unwrap();
                    data_obj.insert("charMap".to_string(), json!(style_data.char_map));
                    data_obj.insert("styleMap".to_string(), json!(style_data.style_map));
                    data_obj.insert("styles".to_string(), json!(style_data.styles));
                }

                json!({
                    "type": "init",
                    "data": data
                })
            },

            Event::Output(_time, seq) => json!({
                "type": "output",
                "data": json!({
                    "seq": seq
                })
            }),

            Event::Resize(_time, cols, rows) => json!({
                "type": "resize",
                "data": json!({
                    "cols": cols,
                    "rows": rows,
                })
            }),

            Event::Snapshot(cols, rows, seq, text, style_data) => {
                let mut data = json!({
                    "cols": cols,
                    "rows": rows,
                    "seq": seq,
                    "text": text,
                });

                if let Some(style_data) = style_data {
                    let data_obj = data.as_object_mut().unwrap();
                    data_obj.insert("charMap".to_string(), json!(style_data.char_map));
                    data_obj.insert("styleMap".to_string(), json!(style_data.style_map));
                    data_obj.insert("styles".to_string(), json!(style_data.styles));
                }

                json!({
                    "type": "snapshot",
                    "data": data
                })
            },

            Event::Pid(_time, pid) => json!({
                "type": "pid",
                "data": json!({
                    "pid": pid
                })
            }),

            Event::ExitCode(_time, exit_code) => json!({
                "type": "exitCode",
                "data": json!({
                    "exitCode": exit_code
                })
            }),

            Event::Debug(_time, message) => json!({
                "type": "debug",
                "data": json!({
                    "message": message
                })
            }),

            Event::Completed(time) => json!({
                "type": "commandCompleted",
                "data": json!({
                    "time": time
                })
            }),
        }
    }
}

fn build_vt(cols: usize, rows: usize) -> avt::Vt {
    avt::Vt::builder().size(cols, rows).build()
}

fn resize_vt(vt: &mut avt::Vt, cols: usize, rows: usize) {
    vt.feed_str(&format!("\x1b[8;{rows};{cols}t"));
}

impl Client {
    pub fn accept(self, subscription: Subscription) {
        let _ = self.0.send(subscription);
    }
}

pub async fn stream(
    clients_tx: &mpsc::Sender<Client>,
) -> Result<impl Stream<Item = Result<Event, BroadcastStreamRecvError>>> {
    let (sub_tx, sub_rx) = oneshot::channel();
    clients_tx.send(Client(sub_tx)).await?;
    let sub = tokio::time::timeout(Duration::from_secs(5), sub_rx).await??;
    let init = stream::once(future::ready(Ok(sub.init)));
    let events = BroadcastStream::new(sub.broadcast_rx);

    Ok(init.chain(events))
}
