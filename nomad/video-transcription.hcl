job "video-transcription" {
  datacenters = ["cluster"]

  # force redeploy
  meta {
    redeploy_uuid = "${uuidv4()}"
  }

  vault {
    policies = ["transcription-policy"]
  }

  group "service" {

    # Target nodes with GPU capability
    constraint {
      attribute = "${meta.gpu-capable}"
      value     = "true"
    }


    network {
      mode = "host"
      port "http" {}  # Dynamic port allocation; no 'static' or 'to'	 
    }


    task "server" {
      driver = "docker"

      resources {
        cpu    = 4000
        memory = 8192
      }

      config {
        image = "registry.cluster:5000/video-transcription-ws:latest"
	network_mode = "host"  # Align Docker with Nomad's host mode
        #volumes = [
        #  "/tmp:/tmp",
        #]
      }
      
      env {
        # AWS Configuration
        AWS_ACCESS_KEY_ID     = "${AWS_ACCESS_KEY_ID}"
        AWS_SECRET_ACCESS_KEY = "${AWS_SECRET_ACCESS_KEY}"
        AWS_REGION            = "us-east-1"
	S3_ENDPOINT = "http://cluster00.cluster"
        
        # Consul Configuration
        CONSUL_HOST           = "consul.service.consul"
        CONSUL_PORT           = "8500"
        
        # Application Configuration
        APP_HOST              = "0.0.0.0"
        APP_PORT              = "${NOMAD_PORT_http}"  # dynamic port here
	ROOT_PATH             = "/transcribe"

	# LOG_LEVEL
	LOG_LEVEL             = "debug"
      }

      # Vault template for AWS credentials
      template {
        data = <<EOF
{{ with secret "secret/data/aws/transcription" }}
AWS_ACCESS_KEY_ID = "{{ .Data.data.access_key }}"
AWS_SECRET_ACCESS_KEY = "{{ .Data.data.secret_key }}"
{{ end }}
EOF
        destination = "secrets/aws.env"
        env         = true
      }

      # Optional: Vault template for HuggingFace token
      template {
        data = <<EOF
{{ with secret "secret/data/hf/transcription" }}
HF_TOKEN = "{{ .Data.data.token }}"
{{ end }}
EOF
        destination = "secrets/hf.env"
        env         = true
      }



      service {
        name = "video-transcription"
        port = "http"
        
        check {
          type     = "http"
          path     = "/health"
          interval = "10s"
          timeout  = "2s"
        }

       tags = [
        "video-transcription",
        "urlprefix-/transcribe strip=/transcribe"
      ]
      }
    }
    
#    task "init" {
#      driver = "docker"
#      
#      config {
#        image = "registry.cluster:5000/video-transcription-ws:6e2c0898-4f01-4971-8ab6-fd451c382e3d"
#      }
#      
#      resources {
#        cpu    = 4000
#        memory = 8192
#      }
#    }
  }
  

}