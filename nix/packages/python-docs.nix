# Python documentation generation
{ flake, pkgs, inputs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) createAnalysisPackage makeCheck;

  # Create a shell script that sets up the environment and runs pdoc
  pdocScript = pkgs.writeShellScript "pdoc-docs" ''
    set -euo pipefail

    # Set up Python environment
    export PYTHONPATH="htty-core/src/python:htty/src:$PYTHONPATH"

    # Ensure docs directory exists
    mkdir -p docs

    # Generate htty-core docs
    cd htty-core
    rm -rf docs
    pdoc --output-directory docs htty_core
    echo '📚 Generated docs in htty-core/docs/ directory'
    cd ..

    # Move htty-core docs to main docs directory
    rm -rf docs/htty-core.g
    mkdir -p docs/htty-core.g
    mv htty-core/docs/* docs/htty-core.g/

    # Generate htty docs
    cd htty
    rm -rf docs
    pdoc --output-directory docs htty
    echo '📚 Generated docs in htty/docs/ directory'
    cd ..

    # Move htty docs to main docs directory
    rm -rf docs/htty.g
    mkdir -p docs/htty.g
    mv htty/docs/* docs/htty.g/

    # Clean up temporary directories
    rm -rf htty/docs htty-core/docs

    echo '📚 Documentation has been generated in docs/ directory'
  '';

  # Create a single check that generates all docs
  pdocCheck = makeCheck {
    name = "pdoc";
    description = "Generate API documentation for htty and htty-core";
    dependencies = with pkgs; [ ];
    command = ''
      nix develop .#pytest-htty --command bash ${pdocScript}
    '';
  };
in
createAnalysisPackage {
  name = "python-docs";
  description = "Python documentation generation";
  checks = {
    pdoc = pdocCheck;
  };
}
