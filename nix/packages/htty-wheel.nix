# Build htty Python wheel with bundled ht binary using maturin
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

  # Platform-specific wheel tags
  platformTag = {
    "x86_64-linux" = "manylinux_2_17_x86_64";
    "aarch64-linux" = "manylinux_2_17_aarch64";
    "x86_64-darwin" = "macosx_10_9_x86_64";
    "aarch64-darwin" = "macosx_11_0_arm64";
  }.${system} or "any";

in
pkgsWithRust.stdenv.mkDerivation {
  pname = "htty-wheel";
  inherit version;
  src = ../..;

  nativeBuildInputs = with pkgsWithRust; [
    rustToolchain
    pkg-config
    python3
    python3.pkgs.pip
    maturin
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
    export PYO3_NO_RECOMPILE=1
    export CARGO_TARGET_DIR="./target"
    
    # Build the wheel with Python bindings
    maturin build --release --features python --out dist/
    
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
    echo "Platform-specific wheel created for: ${system} -> ${platformTag}"
    
    runHook postInstall
  '';

  meta = with pkgs.lib; {
    description = "Headless Terminal - Python wheel with Rust bindings";
    homepage = "https://github.com/MatrixManAtYrService/ht";
    license = licenses.mit;
    platforms = platforms.unix;
  };
}
