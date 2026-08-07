# nodepick.ai Developer Platform

nodepick.ai "node" is a Linux compute server based on MicroVMs. When you create a node, you get a clean, independent machine that belongs entirely to you for the duration of your session. There are no shared kernels, and hardware-level isolation. It's compute that is not bare metal but also not container based, it's sits in the middle and takes the best of both worlds.

This repository contains the developer tools for interacting with nodepick.ai:

- **[Python SDK (`sdk/python`)](sdk/python)**: Programmatic interface for node management.
- **[CLI (`np`)](cli)**: Command-line interface for managing Compute Nodes and SSH keys.

---

## Repository Structure

```
├── cli/         # CLI tool (`np`)
└── sdk/
    └── python/  # Official Python SDK (`nodepick`)
```