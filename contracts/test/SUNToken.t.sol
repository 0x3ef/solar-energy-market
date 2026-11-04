// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {SUNToken} from "../src/SUNToken.sol";

contract SUNTokenTest is Test {
    SUNToken internal token;
    address internal alice = address(0xA11CE);
    address internal bob = address(0xB0B);

    function setUp() public {
        token = new SUNToken();
    }

    function test_MintIncreasesBalance() public {
        token.mint(alice, 100e18);
        assertEq(token.balanceOf(alice), 100e18);
        assertEq(token.totalSupply(), 100e18);
    }

    function test_OnlyOwnerCanMint() public {
        vm.prank(alice);
        vm.expectRevert(SUNToken.NotOwner.selector);
        token.mint(alice, 1e18);
    }

    function test_Transfer() public {
        token.mint(alice, 50e18);
        vm.prank(alice);
        token.transfer(bob, 20e18);

        assertEq(token.balanceOf(alice), 30e18);
        assertEq(token.balanceOf(bob), 20e18);
    }

    function test_TransferInsufficientBalance() public {
        token.mint(alice, 1e18);
        vm.prank(alice);
        vm.expectRevert(SUNToken.InsufficientBalance.selector);
        token.transfer(bob, 2e18);
    }

    function test_ApproveAndTransferFrom() public {
        token.mint(alice, 100e18);
        vm.prank(alice);
        token.approve(bob, 40e18);

        vm.prank(bob);
        token.transferFrom(alice, bob, 40e18);

        assertEq(token.balanceOf(bob), 40e18);
        assertEq(token.allowance(alice, bob), 0);
    }
}