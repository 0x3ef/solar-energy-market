// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {SUNToken} from "../src/SUNToken.sol";
import {EnergyMarketplace} from "../src/EnergyMarketplace.sol";
import {RedemptionManager} from "../src/RedemptionManager.sol";

/// @notice Deploys the full Solar Energy Market stack.
/// @dev Reads `PRIVATE_KEY` and `WEI_PER_TOKEN` from the environment.
contract DeployScript is Script {
    function run() external {
        uint256 deployerKey = vm.envUint("PRIVATE_KEY");
        uint256 weiPerToken = vm.envOr("WEI_PER_TOKEN", uint256(0.001 ether));

        vm.startBroadcast(deployerKey);

        SUNToken token = new SUNToken();
        EnergyMarketplace market = new EnergyMarketplace(address(token));
        RedemptionManager redemption =
            new RedemptionManager(address(token), weiPerToken);

        vm.stopBroadcast();

        console2.log("SUNToken deployed at:", address(token));
        console2.log("EnergyMarketplace deployed at:", address(market));
        console2.log("RedemptionManager deployed at:", address(redemption));

        _writeDeployment(address(token), address(market), address(redemption));
    }

    function _writeDeployment(
        address token,
        address market,
        address redemption
    ) internal {
        string memory json = "deployment";
        vm.serializeAddress(json, "SUNToken", token);
        vm.serializeAddress(json, "EnergyMarketplace", market);
        string memory finalJson =
            vm.serializeAddress(json, "RedemptionManager", redemption);

        string memory path = string.concat(
            "deployments/",
            vm.toString(block.chainid),
            ".json"
        );
        vm.writeJson(finalJson, path);
        console2.log("Deployment written to:", path);
    }
}