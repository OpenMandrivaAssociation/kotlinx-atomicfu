Name:		kotlinx-atomicfu
Version:	0.26.1
Release:	1
Summary:	AtomicFU JVM atomic variables
Group:		Development/Java
License:	Apache-2.0
URL:		https://github.com/Kotlin/kotlinx-atomicfu
# kotlinx-atomicfu tag 0.26.1. JVM artifact atomicfu-jvm: commonMain plus jvmMain.
Source0:	kotlinx-atomicfu-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	java-21-openjdk-devel
BuildRequires:	kotlin
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem
BuildRequires:	mvn(org.jetbrains.kotlin:kotlin-stdlib)

%description
org.jetbrains.kotlinx:atomicfu-jvm %{version}.
JVM atomic references, ints, and longs from kotlinx-atomicfu 0.26.1,
compiled with the installed kotlinc 2.0.21.

%prep
%autosetup -n kotlinx-atomicfu-%{version}
find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print > binaries.list
if [ -s binaries.list ]; then
	cat binaries.list
	exit 1
fi

%build
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-21-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
CPSTD=%{_javadir}/kotlin-stdlib.jar
test -s "$CPSTD"
mkdir -p classes module
find src/common src/jvm -name '*.kt' > sources.list
test "$(wc -l < sources.list)" -eq 9
find src/common -name '*.kt' | paste -sd, - > common.list
common=$(cat common.list)
kotlinc -J-Xmx1g -jvm-target 1.8 -language-version 2.0 -no-stdlib \
	-Xmulti-platform -Xexpect-actual-classes \
	-Xcommon-sources="$common" \
	-cp "$CPSTD" -d classes @sources.list
test -s classes/kotlinx/atomicfu/AtomicInt.class
test -s classes/kotlinx/atomicfu/AtomicFU.class
javac --release 9 \
	--module-path "$CPSTD" \
	--patch-module "kotlinx.atomicfu=$PWD/classes" \
	-d module java9/module-info.java
test -s module/module-info.class
printf '%s\n' 'Manifest-Version: 1.0' > manifest.mf
jar cfm atomicfu-jvm.jar manifest.mf -C classes . -C module .
jar i atomicfu-jvm.jar
desc=$(jar --describe-module --file atomicfu-jvm.jar)
printf '%s\n' "$desc"
if printf '%s\n' "$desc" | grep -F -q 'Unable'; then
	exit 1
fi
printf '%s\n' "$desc" | grep -F -q 'exports kotlinx.atomicfu'
printf '%s\n' "$desc" | grep -F -q 'exports kotlinx.atomicfu.locks'
cat > atomicfu-jvm.pom << END
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.jetbrains.kotlinx</groupId>
  <artifactId>atomicfu-jvm</artifactId>
  <version>%{version}</version>
  <name>atomicfu-jvm</name>
  <description>AtomicFU JVM runtime</description>
  <url>https://github.com/Kotlin/kotlinx-atomicfu</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.jetbrains.kotlin</groupId>
      <artifactId>kotlin-stdlib</artifactId>
      <version>2.0.21</version>
    </dependency>
  </dependencies>
</project>
END


%install
set -eo pipefail
sysjar install --buildroot %{buildroot} \
	--artifact atomicfu-jvm.pom:atomicfu-jvm.jar \
	--file-name atomicfu-jvm \
	--filelist .mfiles
idx="%{buildroot}/usr/share/sysjar/index/org.jetbrains.kotlinx/atomicfu-jvm.sysjar"
test -s "$idx"
grep -F -q '"version": "%{version}"' "$idx"
grep -F -q '"artifactId": "atomicfu-jvm"' "$idx"
test -s %{buildroot}%{_javadir}/atomicfu-jvm.jar

%check
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-21-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
JAR=%{buildroot}%{_javadir}/atomicfu-jvm.jar
test -s "$JAR"
STDLIB=%{_javadir}/kotlin-stdlib.jar
mkdir -p check
cat > check/Atomic.kt << 'EOF'
import kotlinx.atomicfu.atomic

fun main() {
    val counter = atomic(41)
    val next = counter.incrementAndGet()
    if (next != 42 || counter.value != 42) error("atomic")
    println("atomicfu_ok " + next)
}
EOF
kotlinc -J-Xmx1g -jvm-target 1.8 -language-version 2.0 \
	-cp "$JAR:$STDLIB" -d check/out check/Atomic.kt
java -cp "check/out:$JAR:$STDLIB" AtomicKt > check/out.txt
cat check/out.txt
grep -F -qx 'atomicfu_ok 42' check/out.txt

%files -f .mfiles
%license LICENSE.txt
