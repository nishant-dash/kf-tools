### kup

```bash
# run against local environment, this will run juju commands
kup

# view a local bundle
kup -f my-kf-bundle.yaml

# view a remote bundle
kup -t 1.7/stable

# compare a local and a remote bundle
# remote bundle's version is inferred from current bundle
kup -f my-kf-bundle.yaml -t self

# compare a local and remote bundle
kup -f my-kf-bundle.yaml -t 1.7/stable

# compare two local bundles
kup -f my-kf-bundle.yaml -f my-kf-bundle2.yaml

# compare two local bundles and get a yaml/json output
kup -f my-kf-bundle.yaml -f my-kf-bundle2.yaml --format yaml

# generate an action plan based on the differences
kup -f my-kf-bundle.yaml -t 1.7/stable --generate-ap
```