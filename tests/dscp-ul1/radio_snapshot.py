import asyncio,json,socket
from rm500u.at import AsyncATClient
async def main():
    result={'host':socket.gethostname()}
    async with AsyncATClient('/dev/rm500u/modem',timeout=4) as client:
        for key,cmd in [('imsi','AT+CIMI'),('cell','AT+QENG="servingcell"'),('signal','AT+CSQ')]:
            result[key]=str(await client.command(cmd))
    print(json.dumps(result))
asyncio.run(main())
