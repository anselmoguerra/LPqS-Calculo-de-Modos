# Technical Analysis: MODOS2026.xlsm

Source workbook: `arquivo_original/MODOS2026.xlsm`

The original workbook was inspected read-only by reading the `.xlsm` ZIP/XML package contents. No changes were made to the source file.

## Workbook Structure

The workbook has three worksheets:

| Sheet | Visibility | Purpose |
| --- | --- | --- |
| `Todos os Gráficos` | Visible | Main user interface: room inputs, key derived values, and three charts. |
| `Modos por Freqüência` | Visible | Chart-only sheet for the frequency distribution chart. It has no populated cells. |
| `Modos` | Hidden | Calculation sheet. Generates axial, tangential, and oblique modal frequencies, then aggregates them for charts. |

There are no workbook defined names in `xl/workbook.xml`.

## User Inputs

The editable/user-facing inputs are on `Todos os Gráficos`:

| Cell | Label | Current value | Meaning |
| --- | --- | ---: | --- |
| `C4` | `Comprimento (m):` | `3.33` | Room length, used as X dimension. |
| `C5` | `Largura (m):` | `6.4` | Room width, used as Y dimension. |
| `C6` | `Altura (m):` | `2.7` | Room height, used as Z dimension. |
| `C7` | `Temperatura (°C):` | `24` | Air temperature used to estimate speed of sound. |

These cells are the only visible scalar inputs found. The hidden sheet contains seed constants and mode-index tables, but they are implementation data rather than user-facing inputs.

## Visible Sheet Formulas

`Todos os Gráficos` computes:

| Cell/range | Formula | Meaning |
| --- | --- | --- |
| `E4:E6` | `H$6/2/C4` filled down | Primary axial frequency for each room dimension: `c / (2 * dimension)`. |
| `H4` | `C4*C5*C6` | Room volume. |
| `H5` | `2*(C4*C5+C4*C6+C6*C5)` | Total inner surface area for a rectangular room. |
| `H6` | `20.06*SQRT(C7+273)` | Speed of sound from temperature in Celsius. |
| `H7` | `3*H6/MIN(C4:C6)` | Labeled `Freq. de Schroeder`; practically this is `3c / smallest_dimension`. |

With the current inputs, cached values are approximately:

| Output | Value |
| --- | ---: |
| Volume | `57.5424 m3` |
| Total area | `95.166 m2` |
| Speed of sound | `345.7078 m/s` |
| Labeled Schroeder frequency | `384.1198 Hz` |

## Hidden Sheet: `Modos`

The hidden `Modos` sheet is the calculation engine. It links the visible inputs into:

| Cell | Formula | Meaning |
| --- | --- | --- |
| `G1` | `'Todos os Gráficos'!C4` | X/length. |
| `G2` | `'Todos os Gráficos'!C5` | Y/width. |
| `G3` | `'Todos os Gráficos'!C6` | Z/height. |
| `G4` | `20.06*SQRT('Todos os Gráficos'!C7+273)` | Speed of sound. |

The modal frequency formula used throughout is the rectangular-room mode equation:

```text
f = c/2 * sqrt((p/Lx)^2 + (q/Ly)^2 + (r/Lz)^2)
```

The spreadsheet rounds modal frequencies to whole hertz and stores `0` when a result is above `300 Hz`.

### Axial Modes

Rows `8:11` build the axial modes:

| Range | Logic |
| --- | --- |
| `B8:Z8` | Mode index `1..25`. |
| `B9:Z9` | X-axis axial frequencies: `IF(c/2*n/x<=300, ROUND(c/2*n/x,0), 0)`. |
| `B10:Z10` | Y-axis axial frequencies. |
| `B11:Z11` | Z-axis axial frequencies. |

Only one modal index is non-zero at a time for axial modes.

### Tangential Modes

Rows `15:90` build three 25-by-25 tangential mode grids:

| Row block | Dimensions combined | Formula pattern |
| --- | --- | --- |
| `15:40` | X and Y | `c/2*SQRT((p/x)^2+(q/y)^2)` |
| `41:65` | X and Z | `c/2*SQRT((p/x)^2+(q/z)^2)` |
| `66:90` | Y and Z | `c/2*SQRT((p/y)^2+(q/z)^2)` |

Each formula is wrapped as:

```excel
IF(f<=300, ROUND(f,0), 0)
```

Tangential counts are later divided by `2`, apparently to compensate for symmetric duplicate counts in the grid.

### Oblique Modes

Rows `91:1340` build oblique modes. The sheet uses 25 repeated blocks of 50 rows:

| Range/field | Logic |
| --- | --- |
| `D91`, `D141`, ..., `D1291` | First modal index/block counter, `1..25`. |
| `E` column inside each block | Second modal index, `1..50`. |
| `F:AD` inside each row | Third modal index, `1..25`. |

The oblique formula pattern is:

```excel
IF(
  c/2*SQRT((p/x)^2+(q/y)^2+(r/z)^2)<=300,
  ROUND(c/2*SQRT((p/x)^2+(q/y)^2+(r/z)^2),0),
  0
)
```

Oblique counts are later divided by `4`, again likely as a symmetry/duplicate weighting factor.

## Aggregation Logic

Rows `1342:1605` create the chart source data.

### Per-Hz Distribution

| Range | Logic |
| --- | --- |
| `D1344:D1605` | Integer frequency axis from `20` to `281` Hz. |
| `E1344:E1605` | `LOG(D/20)`, used as a logarithmic x-axis helper. |
| `G1344:G1605` | Axial count per Hz: `COUNTIF(B$9:Z$11,D1344)`. |
| `H1344:H1605` | Tangential weighted count per Hz: `COUNTIF(B$16:Z$90,D1344)/2`. |
| `I1344:I1605` | Oblique weighted count per Hz: `COUNTIF(F$91:AD$1340,D1344)/4`. |

### Frequency-Band Summary

Rows `1346:1356` summarize standard-ish bands:

```text
25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250 Hz
```

Columns `N:P` sum axial, tangential, and oblique counts over frequency slices. Because the formulas are shared across columns, the visible master formula `SUM(G1346:G1352)` in column `N` shifts to the tangential and oblique columns when copied to `O` and `P`.

| Range | Logic |
| --- | --- |
| `N1346:P1356` | Band sums by mode type. |
| `R1346:R1356` | Total weighted modes by band: `SUM(N:P)`. |
| `T1346:T1356` | Modal density: `R / band_center_frequency`. |

## Charts

The workbook contains four chart XML parts:

| Chart part | Title | Data source | Placement |
| --- | --- | --- | --- |
| `chart1.xml` | `Modos por Freqüência - Ponderado` | `Modos!$D$1344:$D$1604` vs `G:H:I` counts | On `Todos os Gráficos`. |
| `chart2.xml` | `Modos por Banda` | `Modos!$L$1346:$L$1356` vs `R1346:R1356` | On `Todos os Gráficos`. |
| `chart3.xml` | `Densidade Modal` | `Modos!$L$1346:$L$1356` vs `T1346:T1356` | On `Todos os Gráficos`. |
| `chart4.xml` | `Modos por Freqüência - Ponderado` | Same source pattern as `chart1.xml` | On `Modos por Freqüência`. |

The hidden `Modos` sheet also embeds one image object, `xl/media/image1.png`, via `drawing3.xml`.

## VBA Macros

The workbook includes `xl/vbaProject.bin`, so it is macro-enabled. Source extraction was limited because no local VBA/OLE extraction library is installed, but binary strings show these VBA components:

```text
Module1
ThisWorkbook
Sheet1
Sheet2
Sheet3
```

The accessible macro text indicates one recorded macro:

```vb
Sub Red()
    Selection.Interior.ColorIndex = ...
    Selection.Font.Bold = True
End Sub
```

The metadata says the macro was recorded on `12/5/2004` by `Sólon do Valle` and has shortcut `Ctrl+f`. It appears to be a formatting macro that colors the current selection and makes its font bold. No workbook event procedure or calculation macro was visible from the available string extraction.

## Calculation Behavior

Calculation is formula-driven. The workbook has a calculation chain (`xl/calcChain.xml`) and uses Excel formulas rather than VBA to perform the modal analysis.

The calculation flow is:

1. User edits room dimensions and temperature on `Todos os Gráficos!C4:C7`.
2. Visible formulas compute basic room metrics and speed of sound.
3. Hidden sheet `Modos` imports those inputs into `G1:G4`.
4. `Modos` enumerates axial, tangential, and oblique mode frequencies up to `300 Hz`.
5. Frequencies are rounded to integer hertz; frequencies above `300 Hz` become `0`.
6. Counts by integer frequency are generated with `COUNTIF`.
7. Counts are weighted by mode family: axial full count, tangential `/2`, oblique `/4`.
8. Frequency bands and modal density are aggregated from the per-Hz counts.
9. Charts read directly from the hidden aggregation ranges.

## Notes and Limitations

- The hidden sheet dimension is `A1:AX1605` and contains `37,162` formula cells.
- `Modos por Freqüência` has no populated worksheet cells; it only hosts a chart.
- The workbook was created in Microsoft Macintosh Excel, originally by `Sólon do Valle`, and last modified by `Usuário do Microsoft Office`.
- VBA was identified from `vbaProject.bin` strings, not fully decompiled. A full VBA audit would require an OLE/VBA extraction tool such as `oletools` or equivalent.
