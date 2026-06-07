import {
  ChatInputCommandInteraction,
  PermissionFlagsBits,
  SlashCommandBuilder,
} from "discord.js"
import { Command } from "../../shared/types/command"
import { component } from "../../utils"
import { add_authorized_user, get_authorized_user_ids, is_authorized_user } from "../../utils/authorized_users"

const authorize_user_add_command: Command = {
  data: new SlashCommandBuilder()
    .setName("authorize-user-add")
    .setDescription("Add a user to the authorized user list")
    .addUserOption((option) =>
      option
        .setName("user")
        .setDescription("User to authorize")
        .setRequired(true)
    )
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator) as SlashCommandBuilder,

  execute: async (interaction: ChatInputCommandInteraction) => {
    if (!is_authorized_user(interaction.user.id)) {
      const denied_message = component.build_message({
        components: [
          component.container({
            components: [
              component.text([
                "## Access Denied",
                "",
                "Only authorized users can add new authorized users.",
              ]),
            ],
          }),
        ],
      })

      await interaction.reply({
        ...denied_message,
        ephemeral : true,
      })
      return
    }

    const user = interaction.options.getUser("user", true)
    const result = add_authorized_user(user.id)
    const authorized_count = get_authorized_user_ids().length

    const response_message = component.build_message({
      components: [
        component.container({
          components: [
            component.text([
              result.added ? "## Authorized User Added" : "## Already Authorized",
              "",
              result.user_id
                ? `<@${result.user_id}> is now in the authorized user list.`
                : "Failed to authorize that user.",
              `Total authorized users: ${authorized_count}`,
            ]),
          ],
        }),
      ],
    })

    await interaction.reply({
      ...response_message,
      ephemeral : true,
    })
  },
}

export default authorize_user_add_command
