import {
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  ContainerBuilder,
  SectionBuilder,
  SeparatorBuilder,
  SeparatorSpacingSize,
  StringSelectMenuBuilder,
  TextDisplayBuilder,
  ThumbnailBuilder,
} from "discord.js"

type text_like = string | string[]

type text_node = {
  kind  : "text"
  lines : string[]
}

type thumbnail_node = {
  kind : "thumbnail"
  url  : string
}

type button_node = {
  custom_id? : string
  kind       : "button"
  label      : string
  style      : "link" | "secondary"
  url?       : string
}

type select_menu_node = {
  custom_id   : string
  kind        : "select_menu"
  options     : Array<{ description?: string; label: string; value: string }>
  placeholder : string
}

type section_node = {
  accessory? : button_node | thumbnail_node
  content    : string
  kind       : "section"
}

type divider_node = {
  kind    : "divider"
  spacing : number
}

type container_node = {
  accent_color? : number
  components    : component_node[]
  kind          : "container"
}

type component_node =
  | button_node
  | container_node
  | divider_node
  | section_node
  | select_menu_node
  | text_node
  | thumbnail_node

function __normalize_lines(value: text_like): string[] {
  return Array.isArray(value) ? value : [value]
}

function __build_button(node: button_node): ButtonBuilder {
  if (node.style === "link" && node.url) {
    return new ButtonBuilder()
      .setStyle(ButtonStyle.Link)
      .setLabel(node.label)
      .setURL(node.url)
  }

  return new ButtonBuilder()
    .setStyle(ButtonStyle.Secondary)
    .setLabel(node.label)
    .setCustomId(node.custom_id || node.label)
}

function __build_thumbnail(node: thumbnail_node): ThumbnailBuilder {
  return new ThumbnailBuilder()
    .setURL(node.url)
    .setDescription("thumbnail")
}

function __build_text_display(lines: string[]): TextDisplayBuilder {
  return new TextDisplayBuilder().setContent(lines.join("\n"))
}

function __append_to_container(container: ContainerBuilder, node: component_node): void {
  if (node.kind === "container") {
    for (const child of node.components) {
      __append_to_container(container, child)
    }
    return
  }

  if (node.kind === "text") {
    container.addTextDisplayComponents(__build_text_display(node.lines))
    return
  }

  if (node.kind === "section") {
    const section = new SectionBuilder()
      .addTextDisplayComponents(new TextDisplayBuilder().setContent(node.content))

    if (node.accessory?.kind === "button") {
      section.setButtonAccessory(__build_button(node.accessory))
    }

    if (node.accessory?.kind === "thumbnail") {
      section.setThumbnailAccessory(__build_thumbnail(node.accessory))
    }

    container.addSectionComponents(section)
    return
  }

  if (node.kind === "divider") {
    const spacing = node.spacing >= 2 ? SeparatorSpacingSize.Large : SeparatorSpacingSize.Small
    container.addSeparatorComponents(
      new SeparatorBuilder()
        .setDivider(true)
        .setSpacing(spacing)
    )
    return
  }

  if (node.kind === "button") {
    container.addActionRowComponents(
      new ActionRowBuilder<ButtonBuilder>().addComponents(__build_button(node))
    )
    return
  }

  if (node.kind === "select_menu") {
    container.addActionRowComponents(
      new ActionRowBuilder<StringSelectMenuBuilder>().addComponents(
        new StringSelectMenuBuilder()
          .setCustomId(node.custom_id)
          .setPlaceholder(node.placeholder)
          .addOptions(node.options)
      )
    )
    return
  }

  if (node.kind === "thumbnail") {
    container.addSectionComponents(
      new SectionBuilder().setThumbnailAccessory(__build_thumbnail(node))
    )
  }
}

function __build_container(node: container_node): ContainerBuilder {
  const container = new ContainerBuilder()

  if (typeof node.accent_color === "number") {
    container.setAccentColor(node.accent_color)
  }

  for (const child of node.components) {
    __append_to_container(container, child)
  }

  return container
}

export function text(value: text_like): text_node {
  return {
    kind  : "text",
    lines : __normalize_lines(value),
  }
}

export function container(input: { accent_color?: number; components: component_node[] }): container_node {
  return {
    kind         : "container",
    accent_color : input.accent_color,
    components   : input.components,
  }
}

export function section(input: { accessory?: button_node | thumbnail_node; content: string | string[] }): section_node {
  return {
    kind      : "section",
    content   : __normalize_lines(input.content).join("\n"),
    accessory : input.accessory,
  }
}

export function divider(spacing: number = 1): divider_node {
  return {
    kind    : "divider",
    spacing : Math.max(1, spacing),
  }
}

export function thumbnail(url: string): thumbnail_node {
  return {
    kind : "thumbnail",
    url,
  }
}

export function secondary_button(label: string, custom_id: string): button_node {
  return {
    kind  : "button",
    label,
    style : "secondary",
    custom_id,
  }
}

export function link_button(label: string, url: string): button_node {
  return {
    kind  : "button",
    label,
    style : "link",
    url,
  }
}

export function select_menu(
  custom_id: string,
  placeholder: string,
  options: Array<{ description?: string; label: string; value: string }>
): select_menu_node {
  return {
    kind        : "select_menu",
    custom_id,
    placeholder,
    options,
  }
}

export function build_message(input: { components: component_node[] }) {
  const top_level_components = input.components.map((node) => (
    node.kind === "container"
      ? __build_container(node)
      : __build_container({ kind: "container", components: [node] })
  ))

  return {
    components : top_level_components,
    flags      : ["IsComponentsV2"] as const,
  }
}
