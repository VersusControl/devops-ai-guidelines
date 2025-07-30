package config

import (
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Server ServerConfig `yaml:"server"`
	K8s    K8sConfig    `yaml:"kubernetes"`
	Log    LogConfig    `yaml:"logging"`
}

type ServerConfig struct {
	Name        string `yaml:"name"`
	Version     string `yaml:"version"`
	Description string `yaml:"description"`
}

type K8sConfig struct {
	ConfigPath string   `yaml:"configPath"`
	Context    string   `yaml:"context"`
	Namespaces []string `yaml:"namespaces"`
}

type LogConfig struct {
	Level  string `yaml:"level"`
	Format string `yaml:"format"`
}

func Load() (*Config, error) {
	cfg := &Config{
		Server: ServerConfig{
			Name:        "k8s-mcp-server",
			Version:     "1.0.0",
			Description: "Kubernetes MCP Server for AI-powered cluster management",
		},
		K8s: K8sConfig{
			ConfigPath: filepath.Join(os.Getenv("HOME"), ".kube", "config"),
			Namespaces: []string{"default"},
		},
		Log: LogConfig{
			Level:  "info",
			Format: "json",
		},
	}

	if configFile := os.Getenv("CONFIG_FILE"); configFile != "" {
		data, err := os.ReadFile(configFile)
		if err != nil {
			return nil, err
		}
		if err := yaml.Unmarshal(data, cfg); err != nil {
			return nil, err
		}
	}

	return cfg, nil
}
