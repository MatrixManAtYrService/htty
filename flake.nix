{
  description = "htty - Headless Terminal with Python bindings";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    blueprint.url = "github:numtide/blueprint";
    rust-overlay.url = "github:oxalica/rust-overlay";
  };

  outputs = inputs: inputs.blueprint {
    inherit inputs;
    prefix = "nix/";
  };
}
