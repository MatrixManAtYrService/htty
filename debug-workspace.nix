# Simple debug to see what's in workspace without complex inputs
let
  # Use the flake's inputs like the actual file does
  flake = builtins.getFlake (toString ./.);
  inherit (flake) inputs;

  httyWorkspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ./htty;
  };

  pyEnvsWorkspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ./py-envs/htty;
  };
in
{
  httyWorkspaceDeps = builtins.attrNames httyWorkspace.deps.default;
  pyEnvsWorkspaceDeps = builtins.attrNames pyEnvsWorkspace.deps.default;
  pyEnvsFiltered = builtins.attrNames (builtins.removeAttrs pyEnvsWorkspace.deps.default [ "htty_core" ]);
}
