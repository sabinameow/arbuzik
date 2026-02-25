
BASE="http://127.0.0.1:8000"
SEP="────────────────────────────────────────────────"

title() { echo -e "\n\033[1;34m▶ $1\033[0m\n$SEP"; }
step()  { echo -e "\n\033[0;33m→ $1\033[0m"; }

title "STEP 1 — Register users (customer, courier, admin)"

step "Register a customer"
curl -s -X POST "$BASE/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"pass123","role":"customer"}' | python3 -m json.tool

step "Register a courier"
curl -s -X POST "$BASE/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"bob","password":"pass123","role":"courier"}' | python3 -m json.tool

step "Register an admin"
curl -s -X POST "$BASE/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"eve","password":"pass123","role":"admin"}' | python3 -m json.tool

title "STEP 2 — Login (audit: user_login logged for each)"

CUSTOMER_TOKEN=$(curl -s -X POST "$BASE/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"pass123"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))")

COURIER_TOKEN=$(curl -s -X POST "$BASE/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"bob","password":"pass123"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))")

ADMIN_TOKEN=$(curl -s -X POST "$BASE/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"eve","password":"pass123"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))")

echo "Customer token: ${CUSTOMER_TOKEN:0:40}..."
echo "Courier  token: ${COURIER_TOKEN:0:40}..."
echo "Admin    token: ${ADMIN_TOKEN:0:40}..."

title "STEP 3 — Customer creates an order (H3 indexing + event published)"

step "Create order at Eiffel Tower (48.8584, 2.2945)"
ORDER_RESP=$(curl -s -X POST "$BASE/orders" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" \
  -d '{"latitude":48.8584,"longitude":2.2945}')
echo $ORDER_RESP | python3 -m json.tool
H3_INDEX=$(echo $ORDER_RESP | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('h3_index',''))")
ORDER_ID=$(echo $ORDER_RESP | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('order_id',''))")
echo -e "\n  H3 cell: $H3_INDEX  (resolution-9 hex ≈ 0.1 km²)"

step "Create a second order nearby (48.8600, 2.2950)"
curl -s -X POST "$BASE/orders" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" \
  -d '{"latitude":48.8600,"longitude":2.2950}' | python3 -m json.tool

title "STEP 4 — RBAC: courier cannot create an order, customer cannot assign"

step "Courier tries to POST /orders (expect 403)"
curl -s -X POST "$BASE/orders" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $COURIER_TOKEN" \
  -d '{"latitude":48.8584,"longitude":2.2945}' | python3 -m json.tool

step "Customer tries to POST /orders/$ORDER_ID/assign (expect 403)"
curl -s -X POST "$BASE/orders/$ORDER_ID/assign" \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" | python3 -m json.tool

title "STEP 5 — Courier assigns then delivers (events fire in server terminal)"

step "Courier assigns order $ORDER_ID"
curl -s -X POST "$BASE/orders/$ORDER_ID/assign" \
  -H "Authorization: Bearer $COURIER_TOKEN" | python3 -m json.tool

step "Courier marks order $ORDER_ID as delivered"
curl -s -X POST "$BASE/orders/$ORDER_ID/deliver" \
  -H "Authorization: Bearer $COURIER_TOKEN" | python3 -m json.tool

title "STEP 6 — H3 query: all orders in cell $H3_INDEX"
curl -s "$BASE/orders/by-h3/$H3_INDEX" | python3 -m json.tool

title "STEP 7 — H3 aggregation: order counts per H3 cell"
curl -s "$BASE/orders/h3-summary" | python3 -m json.tool

title "STEP 8 — Admin views full audit log"
curl -s "$BASE/audit-logs" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool

title "STEP 9 — Admin views event bus log"
curl -s "$BASE/events" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool

title "STEP 10 — RBAC: customer tries /audit-logs (expect 403)"
curl -s "$BASE/audit-logs" \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" | python3 -m json.tool

echo -e "\n\033[1;32m✓ Demo complete.\033[0m\n"
