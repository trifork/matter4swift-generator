<!--
Copyright (c) 2024 Trifork A/S

SPDX-License-Identifier: MIT
-->

# Matter For Swift

This repository contains the matter4swift code generator.

## Code Generation

Make sure the `connectedhomeip` environment is active by executing

    source <connectedhomeip-project-root>/scripts/active.sh

You can now execute the generator by invoking

    $PW_PROJECT_ROOT/scripts/codegen.py \
        --generator custom:./matter4swift/Generator/:matter_trifork_idl_plugin \
        --option output:<output/path> \
        --option generate_views: \
        --option name:<package-name> \
        <path/to/your.matter>

This command will generate a swift package named `<package-name>` in the directory
`<output/path>`.

Example:

    $PW_PROJECT_ROOT/scripts/codegen.py \
        --generator custom:./Generator/:matter_trifork_idl_plugin \
        --option output:AllClusters \
        --option generate_views: \
        --option name:AllClusters \
        $PW_PROJECT_ROOT/examples/all-clusters-app/all-clusters-common/all-clusters-app.matter

You can omit generation of SwiftUI debug views by removing `--option generate_views:`.


## Available Options

    --option output:<output-path> (required)
    Specifies the path to write generated files to.
    
    --option name:<package-name> (required)
    Specifies the name of the generated swift package
    
    --option generate_views:
    Also generates SwiftUI views that are useful for inspecting Matter devices


## Using the Generated Package

Add the generated package as well as `matter4swift` as package dependencies to
your app.