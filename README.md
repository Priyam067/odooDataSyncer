# Odoo Data Sync Module

This Odoo module provides a flexible solution to synchronize data dynamically between Odoo instances using XML-RPC. It includes robust capabilities for handling complex data structures, including dynamic syncing of one-to-many (O2M) and many-to-one (M2O) relationships, ensuring accurate data migration across multiple instances.

## Features
- **Dynamic Model and Field Syncing**: Sync any model and fields dynamically, with support for many-to-one and one-to-many relationships.
- **Selective Syncing**: Choose specific models and apply custom domains for selective data synchronization.
- **Batch Processing**: Handle large data volumes with configurable main and sub-thread batch sizes.
- **User-Friendly Wizard**: Easily configure and execute data synchronization through a simple wizard interface.

## Installation
1. Download or clone this repository to your Odoo add-ons directory.
2. Install the module from the Odoo Apps menu.

## Configuration
1. In the `Data Sync` menu, create a new sync instance by entering the source Odoo instance URL, database, and credentials.
2. Configure your sync preferences using the provided wizard.

## Usage
1. **Open Sync Wizard**: From the sync instance record, click on 'Open Sync Wizard'.
2. **Select Model and Options**: Choose the model, specify any related models for synchronization, and set thread sizes.
3. **Execute Sync**: Click 'Process Sync' to start the data synchronization.

## Roadmap
- **Asynchronous Syncing**: Future releases will support background sync jobs.
- **Expanded Field Support**: Additional field types (e.g., binary, reference) will be supported in upcoming versions.

## Contributing
We welcome contributions to enhance this module! Please submit a pull request or open an issue for suggestions.

## License
This module is licensed under the MIT License.
