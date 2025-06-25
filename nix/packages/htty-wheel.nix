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

in
pkgsWithRust.stdenv.mkDerivation {
  pname = "htty-wheel";
  inherit version;
  src = ../..;

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

  buildInputs = with pkgsWithRust; [
    # Add any required libraries here
  ] ++ pkgs.lib.optionals pkgs.stdenv.isDarwin [
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
    
    # Create a predictable symlink for easy reference
    WHEEL_FILE=$(ls $out/*.whl | head -1)
    WHEEL_NAME=$(basename "$WHEEL_FILE")
    ln -s "$WHEEL_NAME" "$out/htty-wheel.whl"
    
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
