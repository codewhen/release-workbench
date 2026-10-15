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
  directory-title:
    fontSize: "30px"
    lineHeight: 1.3
    letterSpacing: "-0.02em"
  workflow-title:
    fontSize: "19px"
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

Use the system sans stack for interface text and the monospace stack for YAML and logs. The headline is the project identity; title text introduces panels; body text supports editing; smaller labels and captions explain fields and state. Paragraphs are capped at 75 characters where the layout permits. The mobile brand headline drops to 22px. Workflow Home uses a 30px directory title (26px at 700px) and 19px workflow names; inline form headings use 20px. These surface roles extend the existing type hierarchy.

## Layout

The desktop app is a viewport-height flex column (100dvh, minimum 560px; 480px on short desktop screens). Header, toolbar, banners, footer and run inputs keep their own height; the workspace fills the remaining space with a minimum height of 180px (160px on short desktop screens). Its grid row uses minmax(0, 1fr), with zero-minimum-height children so the list and settings scroll independently instead of growing to fit their content. The flexible graph pairs with a 370px independently scrolling settings panel; the panel narrows to 330px at 1000px. Header and toolbar wrap as needed.

At 700px secondary toolbar controls move behind More controls, inputs retain a readable 16px font, and the app uses document scrolling, the workspace stacks and the settings panel becomes full width with an independently scrolling maximum height of 55dvh. The mobile list occupies a bounded, scrolling 320px graph region, keeping settings reachable regardless of workflow length; YAML uses a 480px region. Initial representation is List at widths up to 1000px; entering the 700px breakpoint automatically switches Canvas to List. The narrow Canvas fallback directs users to List.

Workflow Home follows document flow within a centered container capped at 1180px, with 40px 28px 48px desktop padding and 28px 20px padding at 700px. Directory rows use a flexible identity column, 180px evidence column and action column, with 28px gaps and 24px vertical padding. At 850px evidence moves below identity; at 700px rows stack and Open actions become full width. Search and project filters stack, and two-column inline forms become one column at 700px.

Use the documented spacing scale for repeated rhythm. The implementation also uses local values such as 6px label gaps, 14px node padding, 20px mobile padding and 28px header padding; these are component details rather than an expanded global scale.

## Elevation & Depth

Working surfaces are flat, separated by borders and background tones. The modal alone uses a broad structural shadow and dimmed backdrop, recorded in the sidecar. A moving green border identifies executing cards. Reduced-motion preferences replace the motion with a steady border and disable camera transition animation.

## Shapes

Controls and code blocks use gently rounded corners, workflow nodes slightly softer corners, and dialogs the largest radius. Ordinary controls have a 44px minimum height. Canvas zoom and fit controls have 44px square targets. Desktop connection insertion buttons are circular and 32px; mobile insertion targets grow to at least 44px. Checkboxes remain 18px native controls, so 44px is not a universal rule for every rendered element.

## Components

Buttons use white surfaces and line borders. Primary buttons use dark ink, changing to teal on hover; ordinary buttons use the pale hover surface and teal border. Pressed representation and list buttons use the selected surface. Disabled buttons reduce opacity to one half.

Inputs and text areas use white surfaces, line borders and consistent padding. Text areas resize vertically. Buttons, links, fields and disclosure summaries share a 3px teal focus outline offset by 3px.

Disclosure summaries show a plus when collapsed and a minus when expanded. Inputs and run evidence occupy a collapsed-by-default disclosure below the workspace; its expanded desktop content scrolls within a maximum of 35dvh, while mobile expansion follows document flow.

At the mobile breakpoint, selecting a list step focuses the settings heading and scrolls the details into view. Back to workflow steps restores focus to the selected list button and scrolls to the list.

Workflow nodes carry title, type and status, with a direct Add next action. Selection uses a 2px teal outline offset by 2px. Success and failure borders reinforce explicit outcome labels.

Dialogs use native modal behavior, a labelled heading, Escape cancellation and focus restoration. YAML editing occupies its own representation and settings explanation; pending edits are validated and applied before switching representations, preserving invalid text for correction.

Workflow Home uses border-separated rows rather than raised cards: name and description lead, paths distinguish projects, and written outcome and run counts support selection. Inline registration and creation forms use white surfaces, 6px corners and 24px padding (20px on mobile). Header actions expose their expanded state; loading and empty results use explicit copy. Opening a row enters the editor; returning Home preserves server-side run evidence, with pending editor changes guarded before navigation.

## Do's and Don'ts

- Do retain readable labels alongside status color.
- Do preserve visible keyboard focus and the equivalent list editing path.
- Do use tonal separation and borders for working surfaces.
- Don't treat all headings as a 24–32px scale; panel titles are 22px.
- Don't apply modal shadows to ordinary working surfaces.

## Automation card vocabulary

Command nodes use a rectangular body and terminal icon. If nodes use a diamond with a centered If(a), title and state. Entry, Compute, True and False labels sit outside their respective ports, leaving the decision text clear. True exits at the right tip and False at the bottom tip. Manual checks use rounded gate bodies; reusable workflows use a double outline. Built-in actions use a labelled header and an action-specific icon. Type is visible without relying on outcome color. Selection and written outcome labels remain distinct from the type treatment.

The right-click Add a card menu is a fixed, scrollable overlay using existing surface, ink and accent tokens. The toolbar and List view expose the same picker. Arrow keys, Home/End and Escape support keyboard use; items include a short task description. Ordinary action forms select earlier values and typed constants; opaque references live in Reference details.

## Responsive review refinements

Home’s folder navigation collapses on phones; its toggle and New folder action remain visible. Choose a folder to collapse navigation again. Right-click, Shift+F10 and touch press-and-hold expose the same organization actions. Forms stay inline and use a single column on narrow screens.

Run, Stop, Add card and Save remain directly reachable on mobile. More controls reveals secondary tools; desktop keeps all tools visible. Alerts wrap long workflow names without horizontal clipping. Empty workflows offer Start editing. The run toolbar identifies the whole-workflow passed/skipped count separately from selected-work execution progress. YAML uses a flexible editing region; settings and steps keep independent scrolling.

Saved HTML reports use the same restrained palette, responsive headings, written status badges, a native Jump to a step disclosure, evidence links and readable checksums. Relative evidence links retain their selected project when served. Reports have no scripts or external asset dependencies and remain readable when exported.

## Dropdown menus

All single-value choices use the shared Select component, including Home filters, folder destinations, card settings and required-input dialogs. The trigger keeps a fixed-size chevron vertically centered beside an ellipsized value. Options appear in a constrained, scrollable surface with a selected checkmark and explicit focus treatment. Modal menus belong to their dialog so they remain above the modal backdrop.

Arrow keys navigate enabled options; Home/End jump, typing searches by prefix, Enter selects, Escape cancels the menu, and Tab accepts the active option before moving focus. Required choices show an inline error and focus the first invalid control. Disabled controls and options remain unavailable. Menu bounds adapt to viewport width and available space above or below the trigger.

Canvas zoom and fit controls use fixed 20px Lucide icons centered in 44px buttons. Their SVG fill is disabled, and keyboard focus remains visible outside the control group.

Canvas controls reset the React Flow panel margin and sit 16px above the canvas bottom. The hint ends 72px above the bottom, preserving a 12px gap above the 44px controls even when its text wraps.

The default If diamond uses the white surface fill to separate it from the pale canvas. Execution fills override it with running/passed green, failed red and skipped grey.

## Structured control flow

V2 control cards share the ordinary 228px card width and white fill. Loop has While, Until, Count and For each modes; Try has Body, Catch and Finally ports. Labelled bottom ports connect to independent cards, while Done at the right continues after controlled work finishes. Dashed labelled connections express execution ownership; solid connections express prerequisites. There are no oversized containers or resize/collapse controls. The nested List and Controlled by / Control port selectors expose the same ownership for keyboard and mobile editing. Canvas positions are absolute and never affect execution. Old relative container layouts are normalized for display and persisted on the next edit. Bounds remain explicit; active loops expose iteration and elapsed time without fabricated percentages.

While and Until have a labelled top Condition result input. A returning Condition card connects its data output to this input; the gold dotted return line is distinct from teal dashed control ownership and solid dependencies. Only one return value binds a loop, with the exact JSON field and comparison visible in settings. Manual returns explicitly choose True/False per evaluation.
