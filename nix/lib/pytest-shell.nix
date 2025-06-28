# Reusable function for creating pytest devshells
# Used for creating pytest environments with arbitrary Python packages
{ inputs }:

# Return a function that accepts pkgs like other lib modules
pkgs: {
  # Create a pytest devshell with the specified packages
  makePytestShell =
    { pkgs
    , system
    , perSystem
    , packages ? [ ]
    , # List of packages to include (e.g., Python environments)
      extraBuildInputs ? [ ]
    , # Additional packages to include
      extraShellHook ? ""
    , # Additional shell hook content
    }:
    let
      # Load the test workspace to get pytest and test dependencies
      testWorkspace = inputs.uv2nix.lib.workspace.loadWorkspace {
        workspaceRoot = ../../tests;
      };

      # Create python set with ONLY test dependencies (no htty - that comes from packages)
      pythonSet = (pkgs.callPackage inputs.pyproject-nix.build.packages {
        python = pkgs.python3;
      }).overrideScope (
        pkgs.lib.composeManyExtensions [
          inputs.pyproject-build-systems.overlays.default
          (testWorkspace.mkPyprojectOverlay {
            sourcePreference = "wheel";
          })
        ]
      );

      # Create environment with test dependencies (pytest, etc.)
      # Remove htty from deps since we get it from packages parameter
      testDepsOnly = builtins.removeAttrs testWorkspace.deps.default [ "htty" ];
      testDepsEnv = pythonSet.mkVirtualEnv "test-deps-only" testDepsOnly;

    in
    pkgs.mkShell {
      buildInputs = with pkgs; [
        # Test dependencies (pytest, etc.)
        testDepsEnv

        # Development tools for debugging
        uv
        ruff

        # Nix tools
        nixpkgs-fmt
        nil
      ] ++ packages # Add the specified packages (e.g., htty environments)
      ++ pkgs.lib.optionals pkgs.stdenv.isDarwin [
        pkgs.libiconv
        pkgs.darwin.apple_sdk.frameworks.Foundation
      ] ++ extraBuildInputs; # Add any extra packages

      shellHook = ''
        # Set up Python path: packages first (priority), then test deps
        ${if packages != [] then ''export PYTHONPATH="${builtins.concatStringsSep ":" (map (pkg: "${pkg}/lib/python3.12/site-packages") packages)}:${testDepsEnv}/lib/python3.12/site-packages''${PYTHONPATH:+:$PYTHONPATH}"'' else ''export PYTHONPATH="${testDepsEnv}/lib/python3.12/site-packages''${PYTHONPATH:+:$PYTHONPATH}"''}

        export PATH="${testDepsEnv}/bin:$PATH"

        ${extraShellHook}
      '';
    };
}
