---
name: Workbench
description: A restrained local workflow editor for clear configuration and run evidence.
colors:
  paper: "#f5f8f9"
  surface: "#ffffff"
  ink: "#182a30"
  muted: "#4a6068"
  accent: "#165c73"
  line: "#cbd7db"
  graph: "#edf3f5"
  hover: "#eaf1f4"
  selected: "#e0eaee"
  success: "#146040"
  error: "#a12424"
typography:
  body:
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "16px"
    lineHeight: 1.5
  headline:
    fontSize: "24px"
    fontWeight: 650
    lineHeight: 1.25
    letterSpacing: "-0.025em"
  title:
    fontSize: "22px"
    lineHeight: 1.3
    letterSpacing: "-0.02em"
  label:
    fontSize: "14px"
  caption:
    fontSize: "13px"
  code:
    fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace"
    fontSize: "13px"
    lineHeight: 1.6
rounded:
  control: "6px"
  node: "8px"
  dialog: "12px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  xxl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  button-primary-hover:
    backgroundColor: "{colors.accent}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  workflow-node:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.node}"
    padding: "14px 16px"
---

# Design System: Workbench

## Overview

Operate mode preserves the existing checklist's restrained light palette and legible controls. The system feels practical and calm: cool paper surrounds white working surfaces, with dark text and a muted teal accent distinguishing interaction.

**Key Characteristics:**
- Clear, compact controls with visible keyboard focus.
- Borders and tonal surfaces define working areas.
- Status labels accompany success and error color.

## Colors

The primary teal accent identifies links, focus and selection. Dark ink anchors text and primary actions. Cool paper, white surfaces and pale graph backgrounds distinguish adjacent regions; muted text supports hints, while the line color separates surfaces. Success and error colors identify execution outcomes alongside written status.

## Typography

Use the system sans stack for interface text and the monospace stack for YAML and logs. The headline is the project identity; title text introduces panels; body text supports editing; smaller labels and captions explain fields and state. Paragraphs are capped at 75 characters where the layout permits. The mobile brand headline drops to 22px.

## Layout

The desktop working area pairs a flexible graph with a 370px settings panel; the panel narrows to 330px at 1000px. Header and toolbar wrap as needed. At 700px the work area stacks, the settings panel becomes full width, and the list provides equivalent editing. Initial representation is list at widths up to 1000px. On narrow screens the canvas shows a message directing users to List.

Use the documented spacing scale for repeated rhythm. The implementation also uses local values such as 6px label gaps, 14px node padding, 20px mobile padding and 28px header padding; these are component details rather than an expanded global scale.

## Elevation & Depth

Working surfaces are flat, separated by borders and background tones. The modal alone uses a broad structural shadow and dimmed backdrop, recorded in the sidecar. No interface motion is currently prescribed; reduced-motion preferences disable animations and transitions.

## Shapes

Controls and code blocks use gently rounded corners, workflow nodes slightly softer corners, and dialogs the largest radius. Ordinary controls have a 44px minimum height. Desktop connection insertion buttons are circular and 32px; mobile insertion targets grow to at least 44px. Checkboxes remain 18px native controls, so 44px is not a universal rule for every rendered element.

## Components

Buttons use white surfaces and line borders. Primary buttons use dark ink, changing to teal on hover; ordinary buttons use the pale hover surface and teal border. Pressed representation and list buttons use the selected surface. Disabled buttons reduce opacity to one half.

Inputs and text areas use white surfaces, line borders and consistent padding. Text areas resize vertically. Buttons, links, fields and disclosure summaries share a 3px teal focus outline offset by 3px.

Workflow nodes carry title, type and status, with a direct Add next action. Selection uses a 2px teal outline offset by 2px. Success and failure borders reinforce explicit outcome labels.

Dialogs use native modal behavior, a labelled heading, Escape cancellation and focus restoration. YAML editing occupies its own representation and settings explanation; pending edits are validated and applied before switching representations, preserving invalid text for correction.

## Do's and Don'ts

- Do retain readable labels alongside status color.
- Do preserve visible keyboard focus and the equivalent list editing path.
- Do use tonal separation and borders for working surfaces.
- Don't treat all headings as a 24–32px scale; panel titles are 22px.
- Don't apply modal shadows to ordinary working surfaces.
