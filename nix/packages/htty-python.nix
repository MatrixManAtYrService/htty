# Pure Python package without Rust bindings
{ inputs, pkgs, ... }:

let
  lib = inputs.self.lib pkgs;
  inherit (lib.pypkg) pythonSet workspace;

  # Get project metadata
  pyprojectToml = builtins.fromTOML (builtins.readFile ../../pyproject.toml);
  inherit (pyprojectToml.project) version;

  # Create the htty virtual environment
  httyEnv = pythonSet.mkVirtualEnv "htty-env" workspace.deps.default;

in
# Main htty Python package - clean and simple
pkgs.stdenvNoCC.mkDerivation {
  pname = "htty-python";
  inherit version;
  src = httyEnv;

  buildPhase = ''
    mkdir -p $out/bin
    cp -r $src/* $out/
  '';

  meta = with pkgs.lib; {
    description = "htty is a set of python convenience functions for the ht terminal utility, this package does not contain Rust bindings. Use htty-wheel for full functionality.";
    homepage = "https://github.com/MatrixManAtYrService/ht";
    license = licenses.mit;
    mainProgram = "htty";
    platforms = platforms.unix;
  };
}
