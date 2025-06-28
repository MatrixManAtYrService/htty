# Build htty Python wheel with ht binary using maturin
{ inputs, pkgs, ... }:

let
  # Get overlays for Rust
  overlays = [ inputs.rust-overlay.overlays.default ];
  pkgsWithRust = import inputs.nixpkgs {
    inherit (pkgs.stdenv.hostPlatform) system;
    inherit overlays;
  };

  inherit (pkgs.stdenv.hostPlatform) system;

  rustToolchain = pkgsWithRust.rust-bin.stable.latest.default.override {
    extensions = [ "rust-src" ];
  };

  # Get project metadata
  cargoToml = builtins.fromTOML (builtins.readFile ../../Cargo.toml);
  inherit (cargoToml.package) version;

  # Include only files needed for wheel building (Rust + Python sources)
  wheelSource = pkgs.lib.cleanSourceWith {
    src = ../..;
    filter = path: type:
      let
        baseName = baseNameOf path;
        # Get relative path from project root
        projectRoot = toString ../..;
        relPath = pkgs.lib.removePrefix projectRoot (toString path);
      in
      # Include Rust source files
      (pkgs.lib.hasPrefix "/src/rust" relPath) ||
      # Include Python source files
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
      # Include license and readme
      (baseName == "LICENSE") ||
      (baseName == "README.md");
  };

in
pkgsWithRust.stdenv.mkDerivation {
  pname = "htty-wheel";
  inherit version;
  src = wheelSource;

  cargoDeps = pkgsWithRust.rustPlatform.importCargoLock {
    lockFile = ../../Cargo.lock;
  };

  nativeBuildInputs = with pkgsWithRust; [
    rustToolchain
    pkg-config
    python3
    maturin
    rustPlatform.cargoSetupHook
  ];

  buildInputs = pkgs.lib.optionals pkgs.stdenv.isDarwin [
    pkgs.libiconv
    pkgs.darwin.apple_sdk.frameworks.Foundation
  ];

  buildPhase = ''
    runHook preBuild

    # Set up environment for maturin
    export CARGO_TARGET_DIR="./target"

    # Build the wheel with binary bindings (no python feature)
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

    echo "Built wheel package: $WHEEL_NAME"

    runHook postInstall
  '';

  meta = with pkgs.lib; {
    description = "Headless Terminal - Python wheel with ht binary";
    homepage = "https://github.com/MatrixManAtYrService/ht";
    license = licenses.mit;
    platforms = platforms.unix;
  };
}
