# Create Python environment with htty-core installed
{ pkgs, perSystem, ... }:

let
  # Get the htty-core wheel from our packages
  httyCoreWheel = perSystem.self.htty-core-wheel;

  # Get project metadata
  pyprojectToml = builtins.fromTOML (builtins.readFile ../../htty-core/pyproject.toml);
  inherit (pyprojectToml.project) version;

in
# Create the Python package first
let
  httyCorePkg = pkgs.python3.pkgs.buildPythonPackage {
    pname = "htty-core";
    inherit version;
    format = "wheel";
    src = httyCoreWheel;

    # Create dist directory and copy wheel
    unpackPhase = ''
      mkdir -p dist
      cp ${httyCoreWheel}/*.whl dist/
    '';

    # No build needed - it's already a wheel
    dontBuild = true;

    meta = with pkgs.lib; {
      description = "Headless Terminal - Rust binary with Python bindings";
      homepage = "https://github.com/MatrixManAtYrService/ht";
      license = licenses.mit;
      platforms = platforms.unix;
    };
  };
in
# Return the environment with our package
(pkgs.python3.withPackages (ps: [ httyCorePkg ])).overrideAttrs (old: {
  passthru = (old.passthru or {}) // {
    tests = {};  # Prevent blueprint from auto-generating problematic tests
  };
})
