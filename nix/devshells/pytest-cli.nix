# pytest devshell with CLI tools but no Python module
{ flake, inputs, system, perSystem, ... }:

let
  pkgs = inputs.nixpkgs.legacyPackages.${system};
  lib = flake.lib pkgs;
in

lib.makePytestShell {
  inherit pkgs system perSystem;
  
  # Use htty-cli which provides both ht and htty commands without Python module
  packages = [ perSystem.self.htty-cli ];
}
