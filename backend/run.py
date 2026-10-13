import os
import uvicorn

if __name__=='__main__':
    uvicorn.run('backend.app:app',host=os.getenv('HOST','0.0.0.0'),port=int(os.getenv('PORT','4173')),
                proxy_headers=False,access_log=False)
