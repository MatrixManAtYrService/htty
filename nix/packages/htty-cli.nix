# CLI package - provides both 'ht' (Rust binary) and 'htty' (Python CLI)
{ inputs, pkgs, ... }:

let
  # Get project metadata
  cargoToml = builtins.fromTOML (builtins.readFile ../../Cargo.toml);
  inherit (cargoToml.package) version;

  # Get overlays for Rust
  overlays = [ inputs.rust-overlay.overlays.default ];
  pkgsWithRust = import inputs.nixpkgs { 
    inherit (pkgs.stdenv.hostPlatform) system; 
    inherit overlays; 
  };

  rustToolchain = pkgsWithRust.rust-bin.stable.latest.default.override {
    extensions = [ "rust-src" ];
  };

  # Get the htty Python library environment (has htty installed)
  httyPylib = inputs.self.packages.${pkgs.system}.htty-pylib;

in
# Build ht binary and create wrapper for htty CLI
pkgsWithRust.stdenv.mkDerivation {
  pname = "htty-cli";
  inherit version;
  src = ../..;

  cargoDeps = pkgsWithRust.rustPlatform.importCargoLock {
    lockFile = ../../Cargo.lock;
  };

  nativeBuildInputs = with pkgsWithRust; [
    rustToolchain
    pkg-config
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
    
    # Build just the CLI binary (no Python bindings)
    cargo build --release --bin ht
    
    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall
    
    # Install the Rust binary
    mkdir -p $out/bin
    cp target/release/ht $out/bin/
    
    # Create htty CLI wrapper that uses the Python library environment
    cat > $out/bin/htty << 'EOF'
#!/usr/bin/env bash
# htty CLI - synchronous batch mode for scripting
exec ${httyPylib}/bin/python -m htty "$@"
EOF
    chmod +x $out/bin/htty
    
    runHook postInstall
  '';

  meta = with pkgs.lib; {
    description = "Headless Terminal - CLI tools (ht + htty)";
    homepage = "https://github.com/MatrixManAtYrService/ht";
    license = licenses.mit;
    platforms = platforms.unix;
    mainProgram = "htty";
  };
}
