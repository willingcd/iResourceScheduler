"""
项目根目录下的 cardinfo 接口调用示例。
调度器内实际接入逻辑在：src/iresourcescheduler/inventory/state_cardinfo.py
（通过 get_cluster_states_from_cardinfo_api / get_cluster_states，并配合环境变量 CARDINFO_API_BASE_URL）。
"""
import requests

ip = "xxx"
url = "https://" + ip + "/ai/api/v1/k8s/resource/cardinfos"

headers = {
    "User-Agent": "yaak",
    "Accept": "*/*",
    # 与调度器一致：Authorization 为完整头值，建议用环境变量 export AUTHORIZATION='...' 再 os.environ 读取
    "Authorization": "xxxxxx",
}

resp = requests.get(url, headers=headers, proxies={"http": "", "https": ""}, verify=False)

if resp.status_code == 200:
    print(resp.json())
else:
    print(resp.status_code)
    print(resp.text)



""" 输出样例
{
  "code": 200,
  "msg": null,
  "data": {
    "Nvidia": {
      "L20": {
        "PASS_THROUGH": {
          "schedulerPolicy": [
            "SPREAD",
            "BINPACK",
            "TOPOLOGY"
          ],
          "passThroughNodes": [
            {
              "nodeName": "work1",
              "slots": [
                “13”
              ],
              "availableCardNum": 1
            }
          ],
          "resourceName": "nvidia.com/gpu"
        },
        "SHARED": {
          "TIME_SLICING": {
            "schedulerPolicy": [
              "SPREAD",
              "BINPACK"
            ],
            "resourceName": "nvidia.com/gpu",
          },
          "VCUDA": {
            "schedulerPolicy": [
              "SPREAD",
              "BINPACK"
            ],
            "vcudaMode": [
              "PREEMPTION",
              "PARTITIONING"
            ]
            "resourceCoreName": "xpu-engine/vcuda-core",
            "resourceMemName": "xpu-engine/vcuda-memory",
            "resourceNumName": "xpu-engine/vcuda-num",
            "preemptionNodes":[
              {
                "nodeName": "work1",
                "slots": [
                  "12",
                  "13"
                ],
                "availableCardNum": 2
              }
            ],
            "partitioningNodes":[
              {
                "nodeName": "work1",
                "slots": [
                  "13"
                ],
                "availableCardNum": 1
              }
            ]
          }
        },
        "PCI_DEVICE_ID": "xxxxxxxx",
      }
    },
    "useXpuEngine": true
  },
  "traceId": "xxxxxxxx"
}
"""