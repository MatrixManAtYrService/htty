# Build htty Python source distribution using uv2nix
{ inputs, pkgs, ... }:

let
  # Load the htty workspace
  workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../../htty;
  };

  # Create python set
  pythonSet = (pkgs.callPackage inputs.pyproject-nix.build.packages {
    python = pkgs.python3;
  }).overrideScope (
    pkgs.lib.composeManyExtensions [
      inputs.pyproject-build-systems.overlays.default
      (workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      })
    ]
  );

  # Get project metadata from htty pyproject.toml
  pyprojectToml = builtins.fromTOML (builtins.readFile ../../htty/pyproject.toml);
  inherit (pyprojectToml.project) version;

in
# Build the htty package as an sdist using uv2nix
  # For a single-project workspace, the project is available in the python set
pythonSet.htty
