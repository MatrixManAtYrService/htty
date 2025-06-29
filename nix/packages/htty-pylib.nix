# Python library package - clean Python environment with just htty
{ inputs, pkgs, ... }:

let
  # Get project metadata
  pyprojectToml = builtins.fromTOML (builtins.readFile ../../pyproject.toml);
  inherit (pyprojectToml.project) version;

  # Get the htty wheel from our packages (built by maturin)
  httyWheel = inputs.self.packages.${pkgs.system}.htty-wheel;

  # Load the pylib workspace
  workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../../py-envs/lib;
  };

  # Override htty to use our wheel (without problematic symlinks)
  pyprojectOverrides = final: prev: {
    htty = prev.htty.overrideAttrs (old: {
      src = httyWheel; # Use the original wheel directory without symlinks
    });
  };

  # Create python set with htty
  pythonSet = (pkgs.callPackage inputs.pyproject-nix.build.packages {
    python = pkgs.python3;
  }).overrideScope (
    pkgs.lib.composeManyExtensions [
      inputs.pyproject-build-systems.overlays.default
      (workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      })
      pyprojectOverrides
    ]
  );

  # Create the Python environment with htty available
  pythonEnv = pythonSet.mkVirtualEnv "htty-pylib" workspace.deps.default;

in
pythonEnv.overrideAttrs (old: {
  name = "htty-${version}";

  meta = with pkgs.lib; {
    description = "Headless Terminal - Python library with CLI";
    homepage = "https://github.com/MatrixManAtYrService/ht";
    license = licenses.mit;
    platforms = platforms.unix;
  };
})
