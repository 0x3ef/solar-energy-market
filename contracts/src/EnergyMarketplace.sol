// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title EnergyMarketplace
/// @notice Order-book marketplace for SUN tokens with on-chain settlement.
/// @dev Orders are matched price-time by the backend, which calls
///      `fillOrder` with the buyer's address. Tokens move atomically.
contract EnergyMarketplace is ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ---------------------------------------------------------------------
    // Types
    // ---------------------------------------------------------------------
    enum OrderType { Sell, Buy }

    struct Order {
        uint256 id;
        address maker;
        OrderType orderType;
        uint256 amount;          // SUN tokens, 18 decimals
        uint256 pricePerToken;   // wei per SUN token
        uint256 remaining;       // remaining SUN tokens
        bool active;
        uint256 createdAt;
    }

    // ---------------------------------------------------------------------
    // State
    // ---------------------------------------------------------------------
    IERC20 public immutable sunToken;
    address public owner;
    uint256 public nextOrderId;

    mapping(uint256 => Order) public orders;

    // ---------------------------------------------------------------------
    // Events
    // ---------------------------------------------------------------------
    event OrderPlaced(
        uint256 indexed orderId,
        address indexed maker,
        OrderType orderType,
        uint256 amount,
        uint256 pricePerToken
    );
    event OrderFilled(
        uint256 indexed orderId,
        address indexed buyer,
        uint256 amount,
        uint256 totalPaid
    );
    event OrderCancelled(uint256 indexed orderId);

    // ---------------------------------------------------------------------
    // Errors
    // ---------------------------------------------------------------------
    error NotOwner();
    error NotMaker();
    error InvalidAmount();
    error InvalidPrice();
    error OrderNotActive();
    error InsufficientPayment();
    error TransferFailed();

    // ---------------------------------------------------------------------
    // Modifiers
    // ---------------------------------------------------------------------
    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    // ---------------------------------------------------------------------
    // Constructor
    // ---------------------------------------------------------------------
    constructor(address _sunToken) {
        sunToken = IERC20(_sunToken);
        owner = msg.sender;
    }

    // ---------------------------------------------------------------------
    // Maker actions
    // ---------------------------------------------------------------------
    /// @notice Place a sell order. The maker must have approved this contract
    ///         to spend `amount` SUN tokens beforehand.
    function placeSellOrder(uint256 amount, uint256 pricePerToken) external returns (uint256) {
        if (amount == 0) revert InvalidAmount();
        if (pricePerToken == 0) revert InvalidPrice();

        uint256 orderId = nextOrderId++;
        orders[orderId] = Order({
            id: orderId,
            maker: msg.sender,
            orderType: OrderType.Sell,
            amount: amount,
            pricePerToken: pricePerToken,
            remaining: amount,
            active: true,
            createdAt: block.timestamp
        });

        sunToken.safeTransferFrom(msg.sender, address(this), amount);

        emit OrderPlaced(orderId, msg.sender, OrderType.Sell, amount, pricePerToken);
        return orderId;
    }

    /// @notice Cancel an open order. Refunds remaining tokens to the maker.
    function cancelOrder(uint256 orderId) external nonReentrant {
        Order storage order = orders[orderId];
        if (order.maker != msg.sender) revert NotMaker();
        if (!order.active) revert OrderNotActive();

        order.active = false;
        uint256 refund = order.remaining;
        order.remaining = 0;

        if (refund > 0) {
            sunToken.safeTransfer(msg.sender, refund);
        }

        emit OrderCancelled(orderId);
    }

    // ---------------------------------------------------------------------
    // Filler action (called by backend after matching off-chain)
    // ---------------------------------------------------------------------
    /// @notice Fill part or all of a sell order.
    /// @param orderId     Order to fill.
    /// @param fillAmount  SUN tokens to buy from this order.
    /// @param buyer       Address that receives the SUN tokens.
    function fillOrder(uint256 orderId, uint256 fillAmount, address buyer)
        external
        payable
        nonReentrant
    {
        Order storage order = orders[orderId];
        if (!order.active) revert OrderNotActive();
        if (fillAmount == 0 || fillAmount > order.remaining) revert InvalidAmount();

        uint256 totalCost = (fillAmount * order.pricePerToken) / 1e18;
        if (msg.value < totalCost) revert InsufficientPayment();

        order.remaining -= fillAmount;
        if (order.remaining == 0) {
            order.active = false;
        }

        // Deliver tokens to buyer.
        sunToken.safeTransfer(buyer, fillAmount);

        // Pay the maker. Revert on failure so state rolls back.
        (bool ok,) = payable(order.maker).call{value: totalCost}("");
        if (!ok) revert TransferFailed();

        // Refund any overpayment to the caller.
        if (msg.value > totalCost) {
            (bool refundOk,) = payable(msg.sender).call{value: msg.value - totalCost}("");
            if (!refundOk) revert TransferFailed();
        }

        emit OrderFilled(orderId, buyer, fillAmount, totalCost);
    }

    // ---------------------------------------------------------------------
    // Views
    // ---------------------------------------------------------------------
    function getOrder(uint256 orderId) external view returns (Order memory) {
        return orders[orderId];
    }

    function isActive(uint256 orderId) external view returns (bool) {
        return orders[orderId].active;
    }
}