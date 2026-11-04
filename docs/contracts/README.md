# Contracts

The `contracts/` module is a Foundry project that contains the three
Solidity contracts powering the marketplace and the SUN token. It is
independent from the backend: the backend only consumes the ABI
artifacts produced by `forge build`.

## 1. Contracts

| Contract | File | Purpose |
|---|---|---|
| `SUNToken` | `src/SUNToken.sol` | ERC-20 token representing validated solar energy credits. 1 SUN = 1 kWh of eligible export energy. |
| `EnergyMarketplace` | `src/EnergyMarketplace.sol` | Order-book marketplace for SUN tokens with on-chain settlement in ETH. |
| `RedemptionManager` | `src/RedemptionManager.sol` | Burns SUN and pays the redeemer in ETH at a configurable rate. |

## 2. Roles

| Role | Actor | Capabilities |
|---|---|---|
| Token owner | Backend hot wallet | `SUNToken.mint`, `transferOwnership` |
| Maker | Any user | `EnergyMarketplace.placeSellOrder`, `cancelOrder` |
| Filler | Backend hot wallet | `EnergyMarketplace.fillOrder` |
| Redemption owner | Backend hot wallet | `RedemptionManager.setRate`, `withdraw` |
| Redeemer | Any SUN holder | `RedemptionManager.redeem` |

In the current implementation the backend hot wallet plays three
roles at once (token owner, filler and redemption owner). This is
acceptable for a demo but should be split in production: the token
owner should be a multisig or a timelock, the filler should be a
dedicated relayer and the redemption owner should be a treasury
contract.

## 3. Invariants

The contracts are written so that the following invariants always
hold, and the test suite asserts them where feasible:

### 3.1 SUNToken

- `totalSupply` only increases through `mint`, which is restricted to
  the owner.
- `balanceOf[address]` is always consistent with the emitted
  `Transfer` events.
- `allowance[owner][spender]` never exceeds what the owner approved.

### 3.2 EnergyMarketplace

- The contract holds exactly the sum of `remaining` tokens of all
  active sell orders. `placeSellOrder` pulls the tokens in,
  `fillOrder` pushes them out to the buyer, `cancelOrder` refunds
  them to the maker.
- Every `fillOrder` emits exactly one `OrderFilled` event and
  transfers exactly `fillAmount` tokens plus exactly `fillAmount ×
  pricePerToken` wei to the maker.
- `msg.value` must be at least `fillAmount × pricePerToken`; any
  overpayment is refunded to `msg.sender` in the same transaction.
- A fill larger than `remaining` reverts. An empty fill reverts.
  A fill on an inactive order reverts.

### 3.3 RedemptionManager

- `redeem(amount)` transfers exactly `amount × weiPerToken / 1e18`
  wei to the caller.
- `address(this).balance` never goes below 0; the contract refuses to
  redeem when underfunded.
- Every `Redeemed` event is paired with a `Transfer` from the
  redeemer's wallet to the burn sink (`0xdead`).

## 4. Build and Test

```bash
cd contracts/

# Compile
forge build

# Run the test suite
forge test -vvv

# Coverage report
forge coverage
```

The test suite covers:

- `SUNToken.t.sol` — mint, transfer, approve, transferFrom, owner
  restriction, insufficient balance.
- `EnergyMarketplace.t.sol` — place, fill, cancel, insufficient
  payment, non-maker cancel, full fill closes the order.
- `RedemptionManager.t.sol` — redeem, zero amount, owner-only rate
  update, underfunded contract.

## 5. Deploy

The deploy script deploys all three contracts in the correct order,
sets the redemption rate and writes the addresses to
`deployments/<chainId>.json`.

```bash
# Local Anvil
export PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
export WEI_PER_TOKEN=1000000000000000   # 0.001 ETH per SUN

forge script script/Deploy.s.sol \
  --rpc-url http://127.0.0.1:8545 \
  --broadcast
```

The output includes the addresses of the three contracts. The backend
reads them from `infrastructure/docker/.env` after `./scripts/setup.sh`
injects them automatically.

## 6. ABI Artifacts

`forge build` writes the ABI and bytecode to `contracts/out/`. The
`Dockerfile.backend` copies `contracts/out` into the backend image so
that `TokenService` can load the ABI at runtime:

```dockerfile
COPY contracts/out ./contracts/out
```

The ABI path used by `TokenService` is:

```
/app/contracts/out/SUNToken.sol/SUNToken.json
```

Changing the contract source invalidates the ABI. Re-run `forge build`
before rebuilding the backend image.

## 7. Network Configuration

`foundry.toml` declares two RPC endpoints:

```toml
[rpc_endpoints]
anvil   = "http://127.0.0.1:8545"
sepolia = "${SEPOLIA_RPC_URL}"
```

To deploy to Sepolia, set `SEPOLIA_RPC_URL` in your shell and run:

```bash
forge script script/Deploy.s.sol \
  --rpc-url sepolia \
  --broadcast \
  --verify
```

The deployment JSON is written to
`deployments/11155111.json` (Sepolia chain id). Copy the addresses to
the production environment and rebuild the backend.

## 8. Upgradability

The contracts are **not upgradable** by design. Immutable contracts
are simpler to audit and remove the risk of an upgrade backdoor. If
you later need to change behaviour:

- Deploy a new version of the affected contract.
- Pause the old one if it has a pause mechanism (not implemented
  yet).
- Migrate state through a dedicated migration contract.
- Update the backend environment with the new address.

## 9. Security Considerations

- **Reentrancy** — `EnergyMarketplace` and `RedemptionManager` use
  OpenZeppelin's `ReentrancyGuard` on every function that transfers
  ETH.
- **Integer overflow** — Solidity 0.8.x reverts on overflow by
  default; no `unchecked` blocks are used.
- **Front-running** — the marketplace relies on off-chain matching by
  the backend. A mempool observer could front-run a `fillOrder`, but
  the economic impact is bounded by the order price and the fact that
  the filler pays for the tokens.
- **Access control** — the owner of `SUNToken` is a single address.
  In production this should be a multisig with a timelock. The
  `transferOwnership` function exists precisely to support this
  migration.
- **Burn sink** — `RedemptionManager` sends SUN to `0xdead` because
  `SUNToken` does not expose a `burn` function. This is equivalent to
  burning for economic purposes but keeps the token interface
  minimal. If a `burn` function is added later, switch
  `safeTransferFrom` to `burnFrom`.