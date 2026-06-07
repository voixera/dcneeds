import { AttachmentBuilder } from "discord.js"
import { readFileSync } from "fs"
import { resolve } from "path"

const __bypass_logo_name = "logobypass.png"
const __bypass_logo_path = resolve(process.cwd(), "logo", __bypass_logo_name)

let __bypass_logo_buffer: Buffer | null = null

function __get_bypass_logo_buffer(): Buffer {
  if (!__bypass_logo_buffer) {
    __bypass_logo_buffer = readFileSync(__bypass_logo_path)
  }

  return __bypass_logo_buffer
}

export const bypass_logo_url = `attachment://${__bypass_logo_name}`

export function get_bypass_logo_file(): { content: Buffer; name: string } {
  return {
    content : __get_bypass_logo_buffer(),
    name    : __bypass_logo_name,
  }
}

export function get_bypass_logo_attachment(): AttachmentBuilder {
  const { content, name } = get_bypass_logo_file()
  return new AttachmentBuilder(content, { name })
}
