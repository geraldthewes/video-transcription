***BUILD INSTRUCTIONS***


You must commit any changes to git before launching a new build

You must rebuild the docker image using the Makefile
```
make build
```

Builds use jobforge to build, build results can be retrieved with

```
jobforge get-logs {job-id}
```

You then need to deploy the service to test it

```
make deploy
```

You can test changes with

```
make test
```


Logs on the server can be retrieved using nomad

```
 nomad job status video-transcription
 nomad alloc logs --stderr {Allocation Id}
```

If dealing with fabio, routes can be reviewed using
```
curl http://fabio.service.consul:9998/api/routes
```
