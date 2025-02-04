def extract_message_body(msg):
    """Strip off the message envelope.

    Handle both fedmsg and fedora-messaging style message bodies.
    """

    body = msg.get("body", {})
    if body:
        return body
    else:
        return msg
