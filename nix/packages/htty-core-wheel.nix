# Build htty-core Python wheel (maturin-built with Rust binary)
{ inputs, pkgs, ... }:

let
  # Get overlays for Rust
  overlays = [ inputs.rust-overlay.overlays.default ];
  pkgsWithRust = import inputs.nixpkgs {
    inherit (pkgs.stdenv.hostPlatform) system;
    inherit overlays;
  };

  rustToolchain = pkgsWithRust.rust-bin.stable.latest.default.override {
    extensions = [ "rust-src" ];
  };

  # Get project metadata
  cargoToml = builtins.fromTOML (builtins.readFile ../../htty-core/Cargo.toml);
  inherit (cargoToml.package) version;

  # Include only files needed for htty-core wheel building
  wheelSource = pkgs.lib.cleanSourceWith {
    src = ../../htty-core;
    filter = path: type:
      let
        baseName = baseNameOf path;
        # Get relative path from htty-core root
        projectRoot = toString ../../htty-core;
        relPath = pkgs.lib.removePrefix projectRoot (toString path);
      in
      # Include Rust source files
      (pkgs.lib.hasPrefix "/src/rust" relPath) ||
      # Include Python source files for htty-core
      (pkgs.lib.hasPrefix "/src/python" relPath) ||
      # Include assets directory (needed by rust-embed)
      (pkgs.lib.hasPrefix "/assets" relPath) ||
      # Include directory structure
      (relPath == "/src/rust" && type == "directory") ||
      (relPath == "/src/python" && type == "directory") ||
      (relPath == "/src" && type == "directory") ||
      (relPath == "/assets" && type == "directory") ||
      # Include build configuration files
      (baseName == "Cargo.toml") ||
      (baseName == "Cargo.lock") ||
      (baseName == "pyproject.toml") ||
      # Include readme (referenced in Cargo.toml)
      (baseName == "README.md");
  };

in
pkgsWithRust.stdenv.mkDerivation {
  pname = "htty-core-wheel";
  inherit version;
  src = wheelSource;

  cargoDeps = pkgsWithRust.rustPlatform.importCargoLock {
    lockFile = ../../htty-core/Cargo.lock;
  };

  nativeBuildInputs = with pkgsWithRust; [
    rustToolchain
    pkg-config
    python3
    python3.pkgs.cffi
    maturin
    rustPlatform.cargoSetupHook
  ];

  buildInputs = pkgs.lib.optionals pkgs.stdenv.isDarwin [
    pkgs.libiconv
  ];

  buildPhase = ''
    runHook preBuild

    # Set up environment for cargo and maturin
    export CARGO_TARGET_DIR="./target"

    # First build the Rust binary with cargo
    cargo build --release --bin ht

    # Then use maturin to package the Python module + binary
    maturin build --release --out dist/

    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall

    # Create output directory
    mkdir -p $out

    # Copy the built wheel
    cp dist/*.whl $out/

    # Store wheel metadata for consumers
    WHEEL_FILE=$(ls $out/*.whl | head -1)
    WHEEL_NAME=$(basename "$WHEEL_FILE")

    # Store metadata
    echo "$WHEEL_NAME" > "$out/wheel-filename.txt"
    echo "$WHEEL_FILE" > "$out/wheel-path.txt"

    echo "Built htty-core wheel package: $WHEEL_NAME"

    runHook postInstall
  '';

  meta = with pkgs.lib; {
    description = "Headless Terminal - Rust binary with Python bindings wheel";
    homepage = "https://github.com/MatrixManAtYrService/ht";
    license = licenses.mit;
    platforms = platforms.unix;
  };
}
