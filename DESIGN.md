---
name: Workbench
description: A restrained, local typed-flowchart editor with inspectable run evidence.
colors:
  paper: "#edf3f5"
  surface: "#ffffff"
  ink: "#192e35"
  muted: "#536c76"
  accent: "#17627a"
  line: "#c6d5db"
  success: "#216b49"
  error: "#a52f36"
---

# Workbench design system

## Direction

Operate mode retains cool paper, white working surfaces, system sans typography and teal interaction. The application is a general-purpose typed flowchart workbench. Primary actions and execution evidence lead; advanced settings are disclosed progressively. No remote fonts, paid assets or hosted dependencies.

## Layout

Desktop uses a viewport-height shell with header, wrapping toolbar, function breadcrumbs and footer. The left details panel resizes between 280 and 650px and can be hidden. Its scroll is independent from the canvas/List. Small screens default to List, stack graph above details and use document scrolling; selecting a card brings details into reach. Home uses a searchable workflow directory and folder/project controls rather than a grid of decorative cards.

## Cards and connections

Operations use compact white 268px cards. If has a distinct opposing-corner silhouette; Loop has double side borders; Try has a top accent. Start/Finish are rounded markers. Primary fields are editable on cards; code, bindings and advanced execution settings are in details. Function selectors create/open dedicated flowcharts with breadcrumbs. Layout areas are dotted or collapsible and never alter execution ownership.

Round teal ports with arrowed lines carry execution. Square ochre ports with dashed Value labels carry data. Loop exposes Entry, Body, Next iteration and Done. Main-canvas body cards keep explicit ownership labels. No arbitrary Go To, recursive calls or legacy control modes appear in this preview.

## State and motion

Written labels accompany every color. Passed cards use pale green, failures pale red and skipped/cancelled cards grey. A rotating green running border respects reduced-motion settings. Measured progress is distinguished from a user-supplied estimate; condition-dependent loops do not invent completion percentages. Overall inspection follows active work; deliberate card/canvas/List inspection turns following off.

## Controls and accessibility

Controls use 44px ordinary targets and 44px canvas zoom buttons with fixed 20px Lucide SVGs. Compact embedded card fields remain legible at normal canvas zoom. Custom comboboxes have an aligned fixed chevron, bounded scrollable options, selected checkmarks and Arrow/Home/End/type/Enter/Escape/Tab behavior. Modal menus render inside their dialog. Keyboard List connection controls expose both execution and typed value wiring. Focus uses a visible amber outline; reduced motion disables animated camera movement.

## Verification

Review desktop and mobile together, fix the observed batch once and confirm once. Preserve product behavior while fixing defects. The preview's acceptance record distinguishes executed macOS/browser checks from unverified Windows support.
