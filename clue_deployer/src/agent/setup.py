from setuptools import setup, find_packages

# Read the README file
try:
    with open('README.md', 'r') as readme_file:
        long_description = readme_file.read()
except:
    long_description = "Simple agent to collect metrics from Scraphandre, Kepler, Tapo from a Prometheus"

setup(
    name='psc',
    version='1.1.6',
    description='Simple agent to collect metrics from a Prometheus',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://git.tu-berlin.de/ise/teadal/prometeus-energy-agent',
    author='Sebastian Werner',
    author_email='werner@tu-berlin.de',
    packages=["psc"],
    install_requires=[
        "prometheus-api-client",
        "kubernetes",
        "flask",
        "flask-sock",
        "gunicorn"
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
)
