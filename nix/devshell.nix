{ pkgs, inputs, system, ... }:

let
  # Get test vim from lib using Blueprint pattern
  lib = inputs.self.lib pkgs;
  inherit (lib.testcfg) testVim;
  
  # Get overlays for Rust
  overlays = [ inputs.rust-overlay.overlays.default ];
  pkgsWithRust = import inputs.nixpkgs { 
    inherit system; 
    inherit overlays; 
  };
  
  # Rust toolchain with extensions
  rustToolchain = pkgsWithRust.rust-bin.stable.latest.default.override {
    extensions = [ "rust-src" "clippy" "rustfmt" ];
  };
in
pkgsWithRust.mkShell {
  buildInputs = with pkgsWithRust; [
    # Rust development
    rustToolchain
    pkg-config
    maturin
    
    # Python development  
    python3
    uv
    
    # Additional tools
    ruff
    pyright
    nixpkgs-fmt
    nil
    nixd
    
    # Test dependencies
    testVim
  ] ++ pkgsWithRust.lib.optionals pkgsWithRust.stdenv.isDarwin [
    pkgsWithRust.libiconv
    pkgsWithRust.darwin.apple_sdk.frameworks.Foundation
  ];

  shellHook = ''
    echo "🚀 htty development environment ready!"
    echo "📦 To build Python package: uv run maturin develop"
    echo "🧪 To run tests: uv run pytest"
    echo "🔧 Rust binary: cargo build --release"
    
    export HTTY_TEST_VIM_TARGET="${testVim}/bin/vim"
    
    # Set up environment for maturin
    export CARGO_TARGET_DIR="./target"
  '';
}
