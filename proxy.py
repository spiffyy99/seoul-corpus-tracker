from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from pathlib import Path


class ProxyHandler(SimpleHTTPRequestHandler):

    def do_GET(self):
        if not self.path.startswith("/api/"):
            return super().do_GET()

        headers = {}

        # Forward headers needed for seeking audio.
        for header in ("Range", "If-Range"):
            value = self.headers.get(header)
            if value:
                headers[header] = value

        request = Request(
            f"http://127.0.0.1:5000{self.path}",
            headers=headers,
            method="GET"
        )

        try:
            with urlopen(request) as response:
                self.send_response(response.status)

                for header in (
                    "Content-Type",
                    "Content-Length",
                    "Accept-Ranges",
                    "Content-Range",
                    "Last-Modified",
                    "ETag",
                ):
                    value = response.headers.get(header)
                    if value:
                        self.send_header(header, value)

                self.end_headers()

                # Stream the body rather than reading it all at once.
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)

        except HTTPError as error:
            self.send_response(error.code)

            for header in (
                "Content-Type",
                "Content-Length",
                "Accept-Ranges",
                "Content-Range",
            ):
                value = error.headers.get(header)
                if value:
                    self.send_header(header, value)

            self.end_headers()
            self.wfile.write(error.read())

        except (BrokenPipeError, ConnectionResetError):
            # The browser may stop a request after seeking elsewhere.
            pass

        except Exception as error:
            self.send_error(502, str(error))


if __name__ == "__main__":
    ThreadingHTTPServer(
        ("127.0.0.1", 3000),
        ProxyHandler
    ).serve_forever()