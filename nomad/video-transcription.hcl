job "video-transcription" {
  datacenters = ["cluster"]
  group "service" {

    network {
         mode = "host"
         port "http" {
         to = 8000
       }
    }


    task "server" {
      driver = "docker"



      config {
        image = "video-transcription:latest"
        volumes = [
          "/tmp:/tmp",
        ]
      }
      
      env {
        # AWS Configuration
        AWS_ACCESS_KEY_ID     = "${AWS_ACCESS_KEY_ID}"
        AWS_SECRET_ACCESS_KEY = "${AWS_SECRET_ACCESS_KEY}"
        AWS_REGION            = "${AWS_REGION}"
        
        # Consul Configuration
        CONSUL_HOST           = "consul.service.consul"
        CONSUL_PORT           = "8500"
        
        # Application Configuration
        APP_HOST              = "0.0.0.0"
        APP_PORT              = "8000"
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
        "",
        "urlprefix-/build strip=/build"
      ]
      }
    }
    
    task "init" {
      driver = "docker"
      
      config {
        image = "registry.cluster:5000/video-transcription-ws:latest"
      }
      
      resources {
        cpu    = 4000
        memory = 8192
      }
    }
  }
  
  #constraint {
  #  attribute = "$${attr.kernel.name}"
  #  operator  = "contains"
  #  value     = "linux"
  #}
}