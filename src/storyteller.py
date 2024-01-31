import chatbot


chatbot.Chatbot(
    ENV.get('openai'),
    system='''
You are a children's storyteller.


'''.strip(),
    response_format='json_response',
    debug=True,
)

bot.add_preamble(
    chatbot.build_user_prompt(),
    # chatbot.build_bot_reply(),
)