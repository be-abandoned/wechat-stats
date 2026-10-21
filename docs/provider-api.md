# Local provider API

WeChat Stats does not read any chat database itself. It talks to a **local HTTP provider** that you
run on the same machine, and only ever sees the JSON described below. That keeps the data source
swappable: anything that implements these two endpoints works.

- Base URL: `http://127.0.0.1:5032` by default, override with `CHAT_PROVIDER_URL`.
- Transport: plain HTTP on loopback. No authentication, no TLS, no remote hosts.
- Encoding: `application/json`, UTF-8.
- Responses are wrapped as `{ "ok": true, "data": ... }`. A non-2xx status or `ok: false` aborts the
  pipeline with an error message.

A complete reference implementation with synthetic data lives in
[`tools/mock-provider.js`](../tools/mock-provider.js) — run it with `node tools/mock-provider.js`
and you can exercise the whole dashboard without any real chat data.

## `GET /api/sessions`

Returns the conversations to visualise.

| Query | Type | Meaning |
|---|---|---|
| `limit` | integer | Maximum number of sessions (the client asks for up to 1000). |

Response:

```json
{
  "ok": true,
  "data": [
    {
      "username": "wxid_example",
      "sessionId": "wxid_example",
      "displayName": "Example Contact",
      "sessionName": "Example Contact",
      "lastTimestamp": 1790758768,
      "unreadCount": 0
    }
  ]
}
```

- `username` (required) — stable identifier of the conversation. Sessions whose id ends with
  `@chatroom` (group chats) and known system accounts (`gh_*`, `weixin`, `wxpay`, `*@openim`, …) are
  skipped by the client.
- `displayName` / `sessionName` — used as the dashboard label. Falls back to `username`.
- `lastTimestamp` — Unix seconds. Only used for ordering.

## `GET /api/messages`

Returns messages for one conversation, paginated.

| Query | Type | Meaning |
|---|---|---|
| `session_id` | string | The `username` from `/api/sessions`. |
| `limit` | integer | Page size; the client uses 3000. |
| `offset` | integer | Zero-based offset. The client keeps paging until a page is shorter than `limit`. |

Response:

```json
{
  "ok": true,
  "data": [
    {
      "timestamp": 1790758700,
      "isSelf": true,
      "senderId": "me",
      "type": 1,
      "content": "shipping it friday",
      "localId": 41
    }
  ]
}
```

- `timestamp` — Unix **seconds**. Message ordering and every time bucket in the dashboard derive
  from it.
- `isSelf` — whether this machine's user sent the message. `isSend` (0/1) is accepted as an alias.
- `senderId` — the contact's id for incoming messages; anything else for outgoing.
- `type` — message type; the client maps `1 文本 / 3 图片 / 34 语音 / 43 视频 / 47 表情 / 48 位置 /
  49 链接·文件 / 50 通话 / 10000·10002 系统消息`, everything else becomes "其他".
- `content` — for text messages, used to compute average and maximum text length. Empty for other
  types is fine.
- `localId` — tie-breaker for messages with identical timestamps.

## Guarantees the client relies on

1. `data` is an array; an empty array ends pagination for that conversation.
2. `timestamp` is seconds, not milliseconds.
3. The provider binds to loopback only. The dashboard never contacts anything else, and the pipeline
   sends no telemetry.
4. The provider may return any subset of conversations — the dashboard simply reflects what it gets.

## Implementing your own provider

Any language is fine; two routes and the JSON above are the whole contract. Sketch:

```js
// minimal provider, Node 18+
const http = require('http');
const data = { ok: true, data: [/* sessions or messages */] };
http.createServer((req, res) => {
  res.writeHead(200, { 'content-type': 'application/json' });
  res.end(JSON.stringify(data));
}).listen(5032, '127.0.0.1');
```

Please keep synthetic or anonymised fixtures in any provider you publish — real chat exports must
never be committed to this repository or to a test fixture.
