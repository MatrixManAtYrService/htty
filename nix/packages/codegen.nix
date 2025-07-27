# Code generation tools
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) createAnalysisPackage trimWhitespaceCheck makeGenerateConstantsCheck makeGenerateVersionCheck makeCheck;

  # propagate constants from ../lib/constants.nix
  generateConstantsCheck = makeGenerateConstantsCheck {
    inherit flake;
    files = [
      "htty-core/src/rust/constants.rs"
      "htty-core/src/python/htty_core/constants.py"
      "htty/src/htty/constants.py"
    ];
  };

  # propagate versions from ../lib/version.nix
  generateVersionCheck = makeGenerateVersionCheck {
    inherit flake;
    files = [
      "htty-core/Cargo.toml"
      "htty-core/pyproject.toml"
      "htty/pyproject.toml"
      "htty-core/src/rust/cli.rs"
      "htty/src/htty/cli.py"
      "htty/src/htty/__init__.py"
      "htty-core/src/python/htty_core/__init__.py"
    ];
  };

  # propagate tool configs from common/ folder
  toolConfigFiles = [ "htty-core/pyproject.toml" "htty/pyproject.toml" "tests/pyproject.toml" ];
  toolConfigFilesStr = builtins.concatStringsSep " " toolConfigFiles;
  generateToolConfigsCheck = makeCheck {
    name = "generate-tool-configs";
    description = "Generate tool configurations in pyproject.toml files using Cog from common/ folder";
    dependencies = with pkgs; [ python3 python3Packages.cogapp ];
    environment = lib.cogEnv;
    command = ''
      for file in ${toolConfigFilesStr}; do
        cog -r "$file"
      done
    '';
    verboseCommand = ''
      for file in ${toolConfigFilesStr}; do
        echo "Processing $file..."
        cp "$file" "$file.bak"
        cog -r "$file"
        if ! diff -u "$file.bak" "$file"; then
          echo "Changes made to $file"
        else
          echo "No changes to $file"
        fi
        rm "$file.bak"
        echo
      done
    '';
  };
in
createAnalysisPackage {
  name = "codegen";
  description = "Code generation";
  checks = {
    trim-whitespace = trimWhitespaceCheck;
    generate-constants = generateConstantsCheck;
    generate-version = generateVersionCheck;
    generate-tool-configs = generateToolConfigsCheck;
  };
}
