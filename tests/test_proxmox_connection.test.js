
import pkg from '@jest/globals';
// const { jest } = pkg;

import dotenv from 'dotenv';
import proxmoxApi from 'proxmox-api';

dotenv.config();

// Mock proxmoxApi to avoid real API calls during tests
jest.mock('proxmox-api', () => {
  const mockProxmoxApi = jest.fn();
  mockProxmoxApi.mockImplementation((options) => ({
    nodes: {
      $get: jest.fn()
    }
  }));
  return mockProxmoxApi;
});

describe('Proxmox API Authentication Tests', () => {
  const fakeNodesResponse = [{ node: 'node1' }, { node: 'node2' }];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('should construct Proxmox client with correct tokenID format', () => {
    const authenticate = async () => {
      const proxmox = proxmoxApi({
        host: process.env.PROXMOX_HOST,
        tokenID: `${process.env.PROXMOX_USER}!${process.env.PROXMOX_TOKEN_NAME}`,
        tokenSecret: process.env.PROXMOX_TOKEN_VALUE,
      });

      return proxmox;
    };

    return authenticate().then(() => {
      expect(proxmoxApi).toHaveBeenCalledWith({
        host: process.env.PROXMOX_HOST,
        tokenID: expect.stringMatching(/^.+@.+!.+$/),
        tokenSecret: expect.any(String)
      });
    });
  });

  test('should construct Proxmox client with correct tokenID format and fetch nodes', () => {
    proxmoxApi.mockImplementation(({ tokenID, tokenSecret }) => {
      // Check that tokenID conforms to USER@REALM!TOKENID format
      expect(tokenID).toMatch(/^.+@.+!.+$/);
      expect(tokenSecret).toBeDefined();

      return {
        nodes: {
          $get: jest.fn().mockResolvedValue(fakeNodesResponse),
        },
      };
    });

    const authenticate = async () => {
      const proxmox = proxmoxApi({
        host: process.env.PROXMOX_HOST,
        tokenID: `${process.env.PROXMOX_USER}!${process.env.PROXMOX_TOKEN_NAME}`,
        tokenSecret: process.env.PROXMOX_TOKEN_VALUE,
      });

      const nodes = await proxmox.nodes.$get();
      return nodes;
    };

    return authenticate().then(nodes => {
      expect(nodes).toEqual(fakeNodesResponse);
    });
  });

  test('should complain (throw error) on authentication failure', async () => {
    const errorMsg = 'Authentication failed: Invalid token';

    proxmoxApi.mockImplementation(() => {
      return {
        nodes: {
          $get: jest.fn().mockRejectedValue(new Error(errorMsg)),
        },
      };
    });

    const authenticate = async () => {
      const proxmox = proxmoxApi({
        host: process.env.PROXMOX_HOST,
        tokenID: `${process.env.PROXMOX_USER}!${process.env.PROXMOX_TOKEN_NAME}`,
        tokenSecret: process.env.PROXMOX_TOKEN_VALUE,
      });

      await proxmox.nodes.$get();
    };

    await expect(authenticate()).rejects.toThrow(errorMsg);
  });

  test('should complain if PROXMOX_USER or PROXMOX_TOKEN_NAME env vars are missing', () => {
    // Save originals
    const originalUser = process.env.PROXMOX_USER;
    const originalTokenName = process.env.PROXMOX_TOKEN_NAME;

    // Clear env variables
    process.env.PROXMOX_USER = '';
    process.env.PROXMOX_TOKEN_NAME = '';

    expect(() => {
      const tokenID = `${process.env.PROXMOX_USER}!${process.env.PROXMOX_TOKEN_NAME}`;
      if (!tokenID.match(/^.+@.+!.+$/)) {
        throw new Error('invalid tokenID, format should look be like USER@REALM!TOKENID');
      }
    }).toThrow('invalid tokenID, format should look be like USER@REALM!TOKENID');

    // Restore env variables
    process.env.PROXMOX_USER = originalUser;
    process.env.PROXMOX_TOKEN_NAME = originalTokenName;
  });
});
