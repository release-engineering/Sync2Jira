from gitlab import Gitlab


class GitlabClient:

    def __init__(self, url, token, project):
        self.url = url
        self.token = token
        self.project = project
        self._client = Gitlab(url=url, private_token=token)
        self._project = self._client.get(self.project)

    def fetch_issue(self, iid):
        return self._project.issues.get(iid)

    def fetch_notes_for_issue(self, iid):
        issue = self.fetch_issue(iid)
        return GitlabClient.map_notes_to_intermediary(issue.notes.list(all=True))

    def fetch_mr(self, iid):
        return self._project.mergerequests.get(iid)

    def fetch_notes_for_mr(self, iid):
        mr = self.fetch_mr(iid)
        return GitlabClient.map_notes_to_intermediary(mr.notes.list(all=True))

    @staticmethod
    def map_notes_to_intermediary(notes):
        return [
            {
                "author": note.author.username,
                "name": note.author.name,
                "body": note.body,
                "id": note.id,
                "date_created": note.created_at,
                "changed": note.updated_at,
            }
            for note in notes
        ]
