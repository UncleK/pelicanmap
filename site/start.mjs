import {createArchiveServer} from './server.mjs';
const server=createArchiveServer();
server.listen(48670,'127.0.0.1',()=>console.log('Pelican Map API listening on 127.0.0.1:48670'));
process.on('SIGTERM',()=>server.close(()=>process.exit(0)));
