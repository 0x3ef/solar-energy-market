// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title RedemptionManager
/// @notice Burns SUN tokens and pays the redeemer in native ETH.
/// @dev The owner funds the contract with ETH and sets the redemption
///      rate (wei per SUN token). Users call `redeem` to burn their SUN
///      and receive the corresponding ETH immediately.
contract RedemptionManager is ReentrancyGuard {
    using SafeERC20 for IERC20;

    IERC20 public immutable sunToken;
    address public owner;

    /// @notice Wei paid per whole SUN token (18 decimals).
    uint256 public weiPerToken;

    event Redeemed(
        address indexed user,
        uint256 sunAmount,
        uint256 ethAmount
    );
    event RateUpdated(uint256 oldRate, uint256 newRate);
    event Funded(address indexed from, uint256 amount);

    error NotOwner();
    error RateNotSet();
    error InsufficientContractBalance();
    error TransferFailed();
    error InvalidAmount();

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    constructor(address _sunToken, uint256 _weiPerToken) {
        sunToken = IERC20(_sunToken);
        owner = msg.sender;
        weiPerToken = _weiPerToken;
    }

    /// @notice Set the redemption rate. Only owner (backend).
    function setRate(uint256 _weiPerToken) external onlyOwner {
        uint256 old = weiPerToken;
        weiPerToken = _weiPerToken;
        emit RateUpdated(old, _weiPerToken);
    }

    /// @notice Deposit ETH into the contract to fund redemptions.
    function fund() external payable {
        emit Funded(msg.sender, msg.value);
    }

    /// @notice Burn `sunAmount` SUN from the caller and receive ETH.
    /// @dev The caller must approve this contract to spend `sunAmount`
    ///      before calling. SUN is burned by transferring to address(0)
    ///      only if the token allows it; otherwise we forward to a sink.
    function redeem(uint256 sunAmount) external nonReentrant {
        if (sunAmount == 0) revert InvalidAmount();
        if (weiPerToken == 0) revert RateNotSet();

        uint256 ethAmount = (sunAmount * weiPerToken) / 1e18;
        if (address(this).balance < ethAmount) revert InsufficientContractBalance();

        // Pull SUN from the user and send it to the burn sink.
        sunToken.safeTransferFrom(msg.sender, address(0xdead), sunAmount);

        (bool ok,) = payable(msg.sender).call{value: ethAmount}("");
        if (!ok) revert TransferFailed();

        emit Redeemed(msg.sender, sunAmount, ethAmount);
    }

    /// @notice Withdraw ETH from the contract. Only owner.
    function withdraw(uint256 amount) external onlyOwner {
        if (amount > address(this).balance) revert InsufficientContractBalance();
        if (amount == address(this).balance) {
            // Force-send the final balance so an owner contract without a
            // payable fallback cannot permanently lock redemption funds.
            selfdestruct(payable(owner));
            return;
        }
        (bool ok,) = payable(owner).call{value: amount}("");
        if (!ok) revert TransferFailed();
    }

    receive() external payable {
        emit Funded(msg.sender, msg.value);
    }
}