# EDC15C13 Checksum Corrector (Renault 1.9/2.2 dCi)

A precision Python utility for correcting the 16-bit integrity blocks in **Bosch EDC15C13** ECU firmware. This tool specifically addresses the "no-boot" or "no-communication" state often encountered after applying IMMO OFF patches or manual hex edits to the code logic.

## 🧠 Technical Overview

Unlike standard EDC15 maps that many OBD tools can checksum, the EDC15C13 utilizes a specific integrity block that protects the executable code. If the word sum of this block does not match the stored invariants, the C167 processor will trap and halt.

### Block Specifications
* **Memory Range:** `0x4D000` – `0x7E000`
* **CS1 (Stored Sum):** `0x5FFFC` (2 bytes, Little Endian)
* **CS2 (Complement):** `0x5FFFE` (2 bytes, Little Endian)

### Correction Strategy
The tool employs a **Delta Correction** logic using an original file as a baseline:
1. **Target Identification:** It reads the original file to determine the ECU's expected "target sum."
2. **Two's Complement:** It recalculates CS2 as the negative complement of the modified block's 16-bit word sum.
3. **Restoration:** It ensures CS1 remains synchronized with the original firmware state, satisfying both internal ECU invariants.

## 🚀 Usage

The script requires both the **Original** and **Modified** binaries to correctly calculate the delta.

```bash
python checksum.py <ORIGINAL_FILE> <MODIFIED_FILE>
```

### Process Output
* Scans for byte differences between files.
* Validates checksums for both ORI and MOD versions.
* Generates a third file: `FIXED_<MOD_FILENAME>.bin`.

## 🛠 Requirements

* **Python 3.x**
* Zero external dependencies (uses standard `struct`, `os`, and `sys` libraries).

---

## ⚡ Disclaimer
This tool is designed for professional ECU repair and development. Improperly checksummed files can result in a non-starting vehicle or a bricked ECU. Use at your own risk.

**Developed for Paceworx.**
