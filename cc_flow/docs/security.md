---
title: Security & Disclaimer
---

Keep secrets safe and understand the risks.

## Secrets hygiene

- Store keys only in a local `.env` file (see [Install & Quick Start → Configure](install-quickstart.md#configure) and [Configuration → Environment variables](configuration.md#environment-variables-env))
- Never commit `.env` (already gitignored)
- Use a dedicated API/Agent wallet separate from main funds

## Operational risk

- Autopilot can execute trades automatically (`--skip-confirm`) (see [Autopilot & Scheduling](autopilot.md))
- Leverage increases risk of liquidation
- Network/API failures can cause missed or partial rebalances

## Legal disclaimer

THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

This is PRE-ALPHA software intended as a reference implementation only. Users assume ALL risks associated with using this software, including but not limited to:
- Complete loss of funds
- Trading losses
- Technical failures
- Liquidation risks
- Any other financial losses

CrowdCent does not endorse, recommend, or provide support for any trading strategies, vaults, or implementations using this software. Users must independently verify all functionality and assume full responsibility for their trading decisions.

By using this software, you agree to comply with all applicable laws and regulations, including Hyperliquid's terms of service.


