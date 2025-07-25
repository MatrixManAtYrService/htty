# Single source of truth for version information across htty project
{ pkgs, ... }:

let
  # The code below is generated, see nix/packages/version-bump.nix for the code that generates it.
  #
  # It's also ok to update it by hand.
  # Since the code generation step reads its previous state before generating its new state, your edits will
  # be respected.
  #
  # [[[cog
  # import os
  # cog.outl(f'  major = {os.environ["HTTY_VERSION_MAJOR"]};')
  # cog.outl(f'  minor = {os.environ["HTTY_VERSION_MINOR"]};')
  # cog.outl(f'  patch = {os.environ["HTTY_VERSION_PATCH"]};')
  # cog.outl(f'  prerelease = "{os.environ["HTTY_VERSION_PRERELEASE"]}"; # Set by --prerelease, empty for stable releases')
  # ]]]
  major = 0;
  minor = 2;
  patch = 27;
  prerelease = ""; # Set by --prerelease, empty for stable releases
  # [[[end]]]

  # Get git SHA from current repository
  gitSha = pkgs.lib.substring 0 8 (
    if builtins.pathExists ./../.. && builtins.pathExists ./../../.git then
      builtins.readFile
        (
          pkgs.runCommand "get-git-sha" { } ''
            cd ${toString ./../..}
            ${pkgs.git}/bin/git rev-parse HEAD | tr -d '\n' > $out
          ''
        )
    else
      "unknown"
  );

  # Synthesized version strings from components
  baseVersion = "${builtins.toString major}.${builtins.toString minor}.${builtins.toString patch}";
  version = baseVersion + (if prerelease != "" then "-${prerelease}" else "");
  versionWithGit = "${version}+${gitSha}";
in
{
  # Export version components
  inherit major minor patch prerelease gitSha;

  # Synthesized version strings
  inherit version versionWithGit;

  # Version information for different package formats
  cargo = {
    # Referenced in: htty-core/Cargo.toml
    # Used as: Rust package version
    inherit version;
  };

  python = {
    # Referenced in: htty/pyproject.toml, htty-core/pyproject.toml
    # Used as: Python package version
    inherit version;
  };

  # Display version information for --version flags
  versionInfo = {
    # Referenced in: htty-core/src/rust/main.rs, htty/src/htty/cli.py
    # Used as: Version information displayed by --version flag
    htty = "htty ${version} (${gitSha})";
    htty_core = "htty-core ${version} (${gitSha})";
    ht = "ht ${version} (${gitSha})";
  };
}
