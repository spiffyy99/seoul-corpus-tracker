export async function onRequest(context) {
    return context.env.API_WORKER.fetch(context.request);
}