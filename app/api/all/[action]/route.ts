import { callControl, dynamic } from "../../control";

export { dynamic };

const allowedActions = new Set(["start", "stop"]);

export async function POST(
  _request: Request,
  { params }: { params: { action: string } },
) {
  if (!allowedActions.has(params.action)) {
    return Response.json({ ok: false, error: "Action tidak valid." }, { status: 400 });
  }

  return callControl(`/api/all/${params.action}`, {
    method: "POST",
  });
}
