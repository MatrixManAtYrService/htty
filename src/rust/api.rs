pub mod http;
pub mod stdio;
use std::str::FromStr;

#[derive(Debug, Default, Copy, Clone)]
pub struct Subscription {
    pub init: bool,
    pub snapshot: bool,
    pub resize: bool,
    pub output: bool,
    pub pid: bool,
    pub exit_code: bool,
    pub debug: bool,
    pub command_completed: bool,
}

impl FromStr for Subscription {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let mut sub = Subscription::default();

        for event in s.split(',') {
            match event {
                "init" => sub.init = true,
                "output" => sub.output = true,
                "resize" => sub.resize = true,
                "snapshot" => sub.snapshot = true,
                "pid" => sub.pid = true,
                "exitCode" => sub.exit_code = true,
                "debug" => sub.debug = true,
                "commandCompleted" => sub.command_completed = true,
                _ => return Err(format!("invalid event name: {event}")),
            }
        }

        Ok(sub)
    }
}
