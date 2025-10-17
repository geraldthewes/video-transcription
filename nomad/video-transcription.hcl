job "video-transcription" {
  datacenters = ["dc1"]
  group "service" {
    task "server" {
      driver = "docker"
      
      config {
        image = "video-transcription:latest"
        ports = ["http"]
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
        CONSUL_HOST           = "${CONSUL_HOST}"
        CONSUL_PORT           = "${CONSUL_PORT}"
        
        # Application Configuration
        APP_HOST              = "0.0.0.0"
        APP_PORT              = "8000"
      }
      
      resources {
        cpu    = 500
        memory = 512
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
      }
    }
    
    task "init" {
      driver = "docker"
      
      config {
        image = "alpine:latest"
        command = "/bin/sh"
        args = [
          "-c",
          "mkdir -p /tmp && chmod 777 /tmp"
        ]
      }
      
      resources {
        cpu    = 100
        memory = 64
      }
    }
  }
  
  constraint {
    attribute = "$${attr.kernel.name}"
    operator  = "contains"
    value     = "linux"
  }
}