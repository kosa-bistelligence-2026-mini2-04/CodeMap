class GodObject:
    """Monolithic class with extremely high cyclomatic complexity — CRITICAL CC fixture."""

    def handle_everything(
        self,
        request_type: str,
        payload: dict,
        user_role: str,
        env: str,
        flags: dict,
    ) -> dict:
        response: dict = {}

        if env == "production":
            if user_role == "admin":
                if request_type == "create":
                    if flags.get("allow_create"):
                        if payload.get("name"):
                            if len(payload["name"]) > 3:
                                response["status"] = "created"
                                response["name"] = payload["name"]
                            else:
                                response["status"] = "error"
                                response["reason"] = "name too short"
                        else:
                            response["status"] = "error"
                            response["reason"] = "missing name"
                    else:
                        response["status"] = "forbidden"
                elif request_type == "update":
                    if flags.get("allow_update"):
                        if payload.get("id"):
                            if payload.get("data"):
                                response["status"] = "updated"
                            else:
                                response["status"] = "error"
                                response["reason"] = "missing data"
                        else:
                            response["status"] = "error"
                            response["reason"] = "missing id"
                    else:
                        response["status"] = "forbidden"
                elif request_type == "delete":
                    if flags.get("allow_delete"):
                        if payload.get("id"):
                            response["status"] = "deleted"
                        else:
                            response["status"] = "error"
                            response["reason"] = "missing id"
                    else:
                        response["status"] = "forbidden"
                else:
                    response["status"] = "error"
                    response["reason"] = "unknown request type"
            elif user_role == "editor":
                if request_type == "create":
                    if flags.get("editor_can_create"):
                        response["status"] = "created"
                    else:
                        response["status"] = "forbidden"
                elif request_type == "update":
                    response["status"] = "updated"
                else:
                    response["status"] = "forbidden"
            elif user_role == "viewer":
                if request_type == "read":
                    response["status"] = "ok"
                    response["data"] = payload.get("data", {})
                else:
                    response["status"] = "forbidden"
            else:
                response["status"] = "error"
                response["reason"] = "unknown role"
        elif env == "staging":
            if request_type in ("create", "update", "delete", "read"):
                response["status"] = "ok"
                response["env"] = "staging"
            else:
                response["status"] = "error"
                response["reason"] = "unknown type in staging"
        elif env == "development":
            response["status"] = "ok"
            response["debug"] = True
        else:
            response["status"] = "error"
            response["reason"] = "unknown environment"

        return response
