# Python package utilities
{ inputs, ... }:

pkgs:
let
  inherit (pkgs) python3;

  # Load the workspace from uv.lock
  workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../../.;
  };

  # Create the python package set with proper overlays
  pythonSet = (pkgs.callPackage inputs.pyproject-nix.build.packages {
    python = python3;
  }).overrideScope (
    pkgs.lib.composeManyExtensions [
      inputs.pyproject-build-systems.overlays.default
      (workspace.mkPyprojectOverlay { sourcePreference = "wheel"; })
    ]
  );

  # Build the Python environments that checks will need
  # Development environment with all dependencies for type checking, testing, etc.
  pythonEnvWithDev = pythonSet.mkVirtualEnv "htty-dev-env" workspace.deps.all;

in
{
  inherit pythonSet workspace;
  # Export the Python environments for use in checks
  inherit pythonEnvWithDev;

  # Backward compatibility export with old name
  httyPythonEnvWithDev = pythonEnvWithDev;
}
