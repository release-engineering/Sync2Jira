def extract_message_body(msg):
    """Strip off the message envelope.

    Handle both fedmsg and fedora-messaging style message bodies.
    """

    body = msg.get("msg", {})
    body = body.get("body", body)
    if body:
        return body
    raise KeyError(
        f"Unrecognized message format with keys {msg.keys()}. Expected either 'msg' or 'body'"
    )
